#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'

from docker import errors as docker_errors

from src.node.eclair_Node import *
from src.utils.conf import *
from src.utils.dockerUtilities import *

class eclair_btcController:

    def __init__(self, numberOfContainers=1):
        docker_utilities = DockerUtilities()
        self.eclair_nodes = []

        """
        eclair_tasks = self._get_eclair_tasks()
        if eclair_tasks is not None:
            for swarm_task in eclair_tasks:
                eclair_node = eclair_Node()
                eclair_node.set_swarm_task(swarm_task)
                self.eclair_nodes.append(eclair_node)
        """
        for i in range(numberOfContainers):
            eclair_cont = self._create_container(suffix=i)
            container_node = docker_utilities.get_container_node(eclair_cont)
            eclair_node = eclair_Node()
            eclair_node.set_container_node(container_node)
            self.eclair_nodes.append(eclair_node)

    def _create_container(self, suffix=None):
        docker_utilities = DockerUtilities()

        cont_name = DOCKER_STACK_PREFIX+"_"+ECLAIR_SERVICE_NAME+"."+str(suffix)
        environment = ECLAIR_CONTAINER_ENV
        eclair_cont = None

        try:
            eclair_cont = docker_utilities.docker_client.containers.run(ECLAIR_NODE_IMG_NAME, name=cont_name, network=NETWORK_NAME, environment=environment, detach=True)
        except docker_errors.APIError as de:
            print("Error creating container '"+cont_name+"' from image: "+ECLAIR_NODE_IMG_NAME)
            print de
            exit(1)

        return eclair_cont

if __name__ == '__main__':
    eclair = eclair_btcController(1)