#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
from dockerUtilities import *
from conf import *
from dockerUtilities import *
import json
import time


class bitcoind_Node:

    def __init__(self):
        self.id = ""
        self.container_node = None
        self.ip_add = None

    def _set_bitcoind_info(self):
        self.ip_add = self.container_node.get_container_ip_address()
        return

    def set_container_node(self, container_node):
        self.container_node = container_node
        self._set_bitcoind_info()
        return

    def run_command_in_bitcoind(self, command, quiet=False):
        docker_utilities = DockerUtilities()

        if docker_utilities.is_container_running(self.container_node):
            raise SystemError("The bitcoind container "+self.container_node.get_container_id()+" is not running")

        success, output = docker_utilities.run_docker_command(self.container_node, command)

        if not success:
            print 'There was an error executing command: '+command+', in container: '+self.container_node.get_container_name()
        if not quiet:
            print "$ "+command
            print output
        return output

    def run_bitcoincli_command(self, bitcoincli_command, quiet=False):
        out_js = ""
        output = self.run_command_in_bitcoind(BLOCKCHAIN_COMMAND_PREFIX+bitcoincli_command, quiet)
        try:
            out_js = json.loads(output)
        except ValueError as ve:
            print "Not JSON can be decoded from the output of command:"+BLOCKCHAIN_COMMAND_PREFIX+bitcoincli_command
        return out_js

    def generate_blocks(self, amount, quiet=False):
        return self.run_bitcoincli_command("generate "+str(amount), quiet)

    def get_blockchain_info(self, quiet=False):
        return self.run_bitcoincli_command("getblockchaininfo", quiet)

    def send_funds_to_address(self, address, amount, quiet=False):
        return self.run_bitcoincli_command("sendtoaddress "+address+" "+str(amount), quiet)
