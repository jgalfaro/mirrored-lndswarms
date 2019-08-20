#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'

import docker
import traceback
from socket import timeout as socket_timeout

from src.node.containerNode import *
from src.utils.conf import *


class DockerUtilities:

    def __init__(self):
        self.docker_client = docker.from_env()

    def get_containers_by_prefix_name(self, prefix_name):
        """
        Get the containers running with name prefix_name
        :param prefix_name: A string with the name of the containers to search
        :return: a list of containers object
        """
        containers_nodes = []
        try:
            # Get the service object with the given prefix_name
            running_containers = self.docker_client.containers.list(filters={"name": prefix_name, "desired-state": "running"})
            if len(running_containers) > 0:
                for task in running_containers:
                    print task
                    cont_node = containerNode()
                    cont_node.set_container_id(task["Status"]["ContainerStatus"]["ContainerID"])
                    cont_node.set_pid(task["Status"]["ContainerStatus"]["PID"])
                    cont_node.set_status(task["DesiredState"])

                    if task["NodeID"] == self.local_node_id:
                        cont_node.set_is_local(True)
                        cont = self.docker_client.containers.get(task["Status"]["ContainerStatus"]["ContainerID"])
                        cont_node.set_init_command(cont.attrs["Path"]+" "+" ".join(cont.attrs["Args"]))
                        cont_node.set_init_command = cont.attrs["Config"]["Env"]
                    else:
                        cont_node.set_is_local(False)
                    # IP addresses of the container
                    ip_addresses = []
                    for net in task["NetworksAttachments"]:
                        ip_addresses.extend(net["Addresses"])
                    cont_node.set_swarm_ip_address(ip_addresses)

                    cont_node.set_node_ip_address(self.get_node_ip(task["NodeID"]))

                    # Append the object in the tasks list
                    containers_nodes.append(cont_node)

        except docker.errors.APIError as e:
            print("Error getting the list of running containers")
            traceback.print_exc()
        return containers_nodes

    def get_container_node(self, container):
        """
        Get the containerNode object instance, with info get from the Docker Container object passed as parameter
        :param container: A Docker Container object
        :return: a containerNode object instance
        """
        cont_node = None
        try:
            if isinstance(container, docker.models.containers.Container):
                # Reload container attributes and start setting data to containerNode object
                container.reload()
                cont_node = containerNode()
                cont_node.set_container_id(container.id)
                cont_node.set_pid(container.attrs["State"]["Pid"])
                cont_node.set_status(container.attrs["State"]["Status"])
                cont_node.set_container_ip_address(container.attrs["NetworkSettings"]["Networks"][NETWORK_NAME]["IPAddress"])
                cont_node.set_init_command(container.attrs["Path"]+" "+" ".join(container.attrs["Args"]))
                cont_node.set_init_env(container.attrs["Config"]["Env"])
                cont_node.set_container_name(container.attrs["Name"])

        except docker.errors.APIError as e:
            print("Error getting the list of running containers")
            traceback.print_exc()
            print e

        return cont_node

    def is_container_running(self, container_node):
        """
        Get the actual status of the given container_node Object
        :param container_node: a containerNode instance to determine if is running
        :return: True if the container is up and running, False otherwise
        """
        try:
            container_id = container_node.get_container_id()
            container = self.docker_client.containers.get(container_id)
            if container.attrs["State"]["Status"].lower() == "running":
                return True
            else:
                return False
        except docker.errors.APIError as de:
            print("Error getting the list of running containers")
            traceback.print_exc()
            return False

    def is_container_paused(self, container_node):
        """
        Get the actual status of the given container_node Object
        :param container_node: a containerNode instance to determine if is paused
        :return: True if the container is up and paused, False otherwise
        """
        try:
            container_id = container_node.get_container_id()
            container = self.docker_client.containers.get(container_id)
            if container.attrs["State"]["Status"].lower() == "paused":
                return True
            else:
                return False
        except docker.errors.APIError as de:
            print("Error getting the list of running containers")
            traceback.print_exc()
            return False

    def run_docker_command(self, container_node, command):
        """
        Executes a command on the task container run locally
        :param container_node: a SwarmTask instance of the task to execute the command
        :param command: command to be execute in the task container
        :return: a tuple with (success, output) success will be True if the command was executed
               successfully, False otherwise. output will contain the output from command execution
        """
        output = ""
        try:
            container = self.docker_client.containers.get(container_node.get_container_id())
            success, output = container.exec_run(command)
            if success != 0:
                return False, output
            else:
                return True, output
        except docker.errors.APIError as de:
            print("Error running the command in the container")
            # traceback.print_exc()
            print de
        except socket_timeout as serr:
            print("Error running the command in the container, socket timed out")
            print serr
        return False, output

    def restart_container(self, container_node):
        """
        Restart the container with the ID 'container_id' running the task
        :param container_id: ID of container to be restarted
        """
        try:
            print("Restarting container: ", container_node.get_container_id())
            container = self.docker_client.containers.get(container_node.get_container_id())
            container.restart()
            return True
        except docker.errors.APIError as de:
            print("Error restarting the container")
            traceback.print_exc()
            print de
        return False

    def init_sarwm(self):
        """
        Initialize swarm mode on the Docker host
        """
        try:
            self.docker_client.swarm.init()
        except docker.errors.APIError as de:
            print("Error initializing the swarm mode")
            print de
            exit(1)
        return

    def leave_swarm(self):
        """
        Leave the swarm mode on the Docker host
        """
        try:
            if len(self.docker_client.swarm.attrs) == 0:
                # Local Docker instance does not belong to a Swarm!
                return
            self.docker_client.swarm.leave(force=True)
        except docker.errors.APIError as de:
            print("Error leaving the swarm")
            print de
            exit(1)
        return

    def create_overlay_network(self, name=NETWORK_NAME, subnet=NETWORK_SUBNET, gateway=NETWORK_GATEWAY):
        """
        Create an overlay network on Docker host
        :param name: Name of the network to be created
        :param subnet: Subnet of the network to be created, ie: 192.168.0.0/24
        :param gateway: Gateway of the newtwork to be created, ie: 192.168.0.1
        """

        ipam_pool = docker.types.IPAMPool(subnet=subnet, gateway=gateway)
        ipam_config = docker.types.IPAMConfig(driver="default", pool_configs=[ipam_pool])

        try:
            # An overlay network is usually created in a host belonging to a swarm
            self.init_sarwm()
            self.docker_client.networks.create(name, driver="overlay", attachable=True, ipam=ipam_config)
        except docker.errors.APIError as de:
            print("Error creating overlay network")
            print de
            exit(1)
        return

    def delete_overlay_network(self, name=NETWORK_NAME):
        """
        Delete an overlay network on Docker host
        :param name: Name of the network to be deleted
        """
        try:
            # An overlay network is usually created in host belonging to a swarm
            self.leave_swarm()
            network = self.docker_client.networks.get(name)
            network.remove()
        except docker.errors.NotFound as nf:
            print("Network "+name+" not found")
        except docker.errors.APIError as de:
            print("Error deleting overlay network")
            print de
            exit(1)
        return

if __name__ == '__main__':
    test = DockerUtilities()
    test.create_overlay_network()



