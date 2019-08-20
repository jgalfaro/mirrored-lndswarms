#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'

from docker import errors as docker_errors

from src.node.lnd_Node import *
from src.utils.conf import *
from src.utils.dockerUtilities import *


class lnd_btcController:

    def __init__(self, numberOfContainers=1):
        docker_utilities = DockerUtilities()
        self.lnd_nodes = []
        """
        lnd_tasks = self._get_lnd_tasks()
        if lnd_tasks is not None:
            for swarm_task in lnd_tasks:
                lnd_node = lnd_Node()
                lnd_node.set_swarm_task(swarm_task)
                self.lnd_nodes.append(lnd_node)
        """
        for i in range(numberOfContainers):
            lnd_cont = self._create_container(suffix=i)
            container_node = docker_utilities.get_container_node(lnd_cont)
            lnd_node = lnd_Node()
            lnd_node.set_container_node(container_node)
            self.lnd_nodes.append(lnd_node)

    def _create_container(self, suffix=None):
        docker_utilities = DockerUtilities()

        cont_name = DOCKER_STACK_PREFIX+"_"+LND_SERVICE_NAME+"."+str(suffix)
        environment = LND_CONTAINER_ENV
        lnd_cont = None
        try:
            lnd_cont = docker_utilities.docker_client.containers.run(LND_NODE_IMG_NAME, name=cont_name, network=NETWORK_NAME, environment=environment, detach=True)
        except docker_errors.APIError as de:
            print("Error creating container '"+cont_name+"' from image: "+LND_NODE_IMG_NAME)
            print de
            exit(1)

        return lnd_cont

if __name__ == '__main__':
    lnd = lnd_btcController(3)
