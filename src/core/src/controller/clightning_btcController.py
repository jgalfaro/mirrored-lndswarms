#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'

from docker import errors as docker_errors

from src.node.clightning_Node import *
from src.utils.conf import *
from src.utils.dockerUtilities import *

class clightning_btcController:

    def __init__(self, numberOfContainers=1):
        docker_utilities = DockerUtilities()
        self.clightning_nodes = []

        for i in range(numberOfContainers):
            clightning_cont = self._create_container(suffix=i)
            container_node = docker_utilities.get_container_node(clightning_cont)
            clightning_node = clightning_Node()
            clightning_node.set_container_node(container_node)
            self.clightning_nodes.append(clightning_node)

    def _create_container(self, suffix=None):
        docker_utilities = DockerUtilities()

        cont_name = DOCKER_STACK_PREFIX+"_"+CLIGHTNING_SERVICE_NAME+"."+str(suffix)
        environment = CLIGHTNING_CONTAINER_ENV
        command = CLIGHTNING_CONTAINER_COMMAND

        clightning_cont = None
        try:
            clightning_cont = docker_utilities.docker_client.containers.run(CLIGHTNING_NODE_IMG_NAME, name=cont_name, network=NETWORK_NAME, command=command, environment=environment, detach=True)
        except docker_errors.APIError as de:
            print("Error creating container '"+cont_name+"' from image: "+CLIGHTNING_NODE_IMG_NAME)
            print de
            exit(1)

        return clightning_cont


if __name__ == '__main__':
    ct = clightning_btcController()