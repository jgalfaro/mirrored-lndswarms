#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'

from conf import *
from bitcoind_Node import *
from dockerUtilities import *


class bitcoindController:

    def __init__(self):
        docker_utilities = DockerUtilities()
        bitcoin_container = self._create_container()
        container_node = docker_utilities.get_container_node(bitcoin_container)
        self.bitcoind_node = bitcoind_Node()
        self.bitcoind_node.set_container_node(container_node)

        # self.bitcoind = self._get_bitcoind_task()

    def _create_container(self):
        docker_utilities = DockerUtilities()

        bitcoind_cont = None
        volume_args = {BLOCKCHAIN_VOLUME_NAME: {'bind': BLOCKCHAIN_VOLUME_MOUNT_POINT, 'mode': 'rw'}}
        cont_name = BLOCKCHAIN_CONTAINER_NAME
        environment = BLOCKCHAIN_CONTAINER_ENV
        hostname = BLOCKCHAIN_HOSTNAME
        try:
            bitcoind_cont = docker_utilities.docker_client.containers.run(BLOCKCHAIN_IMG_NAME, name=cont_name, network=NETWORK_NAME, volumes=volume_args, hostname=hostname, environment=environment, detach=True)
        except docker.errors.APIError as de:
            print("Error creating container '"+cont_name+"' from image: "+BLOCKCHAIN_IMG_NAME)
            print de
            exit(1)
        return bitcoind_cont

if __name__ == '__main__':
    bt = bitcoindController()


