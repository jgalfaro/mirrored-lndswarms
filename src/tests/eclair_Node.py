#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
from dockerUtilities import *
from conf import *
from dockerUtilities import *
import json
import time

class eclair_Node:

    def __init__(self):
        self.id = ""
        self.container_node = None
        self.identity_pubkey = None
        self.ip_add = None

    def _set_eclair_info(self):
        info_eclair_node = self.get_info(True)
        self.ip_add = self.container_node.get_container_ip_address()
        self.identity_pubkey = info_eclair_node["nodeId"]
        return

    def set_container_node(self, container_node):
        self.container_node = container_node
        self._set_eclair_info()
        return

    def run_command_in_eclair(self, command, quiet=False):
        docker_utilities = DockerUtilities()

        if docker_utilities.is_container_running(self.container_node):
            raise SystemError("The eclair_btc container "+self.container_node.get_container_id()+" is not running")

        success, output = docker_utilities.run_docker_command(self.container_node, command)
        if not success:
            print 'There was an error executing command: '+command+', in container: '+self.container_node.get_container_name()
        if not quiet:
            print "$ "+command
            print output
        return output

    def run_eclair_api_command(self, eclair_api_command, quiet=False):
        output = self.run_command_in_eclair(ECLAIR_COMMAND_PREFIX+eclair_api_command, quiet)
        try:
            output = json.loads(output)
        except ValueError as ve:
            print "Not JSON can be decoded from the output of command:"+ECLAIR_COMMAND_PREFIX+eclair_api_command
        return output

    def is_eclair_synced_to_chain(self):
        docker_utils = DockerUtilities()
        for i in range(6):
            output = self.run_command_in_eclair(ECLAIR_COMMAND_PREFIX + "getinfo", True)
            eclair_node_info = None
            try:
                eclair_node_info = json.loads(output)
            except ValueError as ve:
                pass
            if not eclair_node_info:
                print "- Warning: ECLAIR daemon is not active yet, waiting 5 seconds"
            else:
                eclair_blockHeight = eclair_node_info["blockHeight"]

                try:
                    bitcoind_container = docker_utils.docker_client.containers.get(BLOCKCHAIN_CONTAINER_NAME)
                    success, output = bitcoind_container.exec_run(BLOCKCHAIN_COMMAND_PREFIX+"getblockchaininfo")
                    blockchain_info = json.loads(output)
                except docker.errors.APIError as de:
                    print("Error getting blockchain info")
                except ValueError as ve:
                    print("Error getting a JSON instance from blockchain info")

                # If the block height are differents, it means that eclair is not synced:
                if blockchain_info["blocks"] != eclair_blockHeight:
                    print "- Warning: ECLAIR node is not synced to chain, waiting 5 seconds"
                else:
                    # ECLAIR node is synced to chain
                    return
            time.sleep(5)

        print "ECLAIR node was not able to synchronize to chain!"
        print "Restarting ECLAIR container node:"+self.container_node.get_container_name()
        if not docker_utils.restart_container(self.container_node):
            exit(1)

    def is_eclair_daemon_active(self):
        for i in range(6):
            output = self.run_command_in_eclair(ECLAIR_COMMAND_PREFIX + "getinfo", True)
            eclair_node_info = None
            try:
                eclair_node_info = json.loads(output)
            except ValueError as ve:
                pass
            if not eclair_node_info:
                print "- Warning: ECLAIR daemon is not active yet, waiting 5 seconds"
            else:
                return
            time.sleep(5)

        print "ECLAIR was not active after waiting time!"
        exit(1)

    def get_info(self, quiet=False):
        self.is_eclair_daemon_active()
        return self.run_eclair_api_command("getinfo", quiet)

    def channel_balance(self, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        return self.run_eclair_api_command("channels", quiet)

    def wallet_balance(self, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        return self.run_eclair_api_command("audit", quiet)

    def list_peers(self, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        return self.run_eclair_api_command("peers", quiet)

    def list_channels(self, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        return self.run_eclair_api_command("channels", quiet)

    def connect_to_node(self, identity_pubkey, ip_addr, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        return self.run_eclair_api_command("connect "+identity_pubkey+" "+ip_addr, quiet)

    def open_channel(self, identity_pubkey, local_amount, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        return self.run_eclair_api_command("open "+identity_pubkey+" "+str(local_amount), quiet)

    def close_channel(self, funding_txid, output_index, quiet=False):
        # First check synchronization to chain
        #self.is_eclair_synced_to_chain()
        channels = self.list_channels(True)
        for channel in channels:
            if channel["channelPoint"] == funding_txid+":"+output_index:
                return self.run_eclair_api_command("close "+channel["channelId"], quiet)

    def add_invoice(self, amount, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        date_string = str(time.time()).strip('.')
        output = self.run_eclair_api_command("receive "+str(amount)+" "+"desc_"+date_string, quiet=True)
        if self.parse_invoice(output, quiet=True)["nodeId"] == self.identity_pubkey:
            print "$ "+ ECLAIR_COMMAND_PREFIX + "receive "+str(amount)+" "+"desc_"+date_string
            print output
            return output
        else:
            print "Error creating an invoice in ECLAIR node:"
            print "$ " + ECLAIR_COMMAND_PREFIX + "receive "+str(amount)+" "+"desc_"+date_string
            print output
            return None

    def send_payment(self, payment_request, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        return self.run_eclair_api_command("send "+payment_request, quiet)

    def parse_invoice(self, payment_request, quiet=False):
        # First check synchronization to chain
        return self.run_eclair_api_command("parseinvoice " + payment_request, quiet)

    def is_channel_active(self, funding_txid, output_index):
        channels = self.list_channels(True)
        for channel in channels:
            print "Channel active value: " + str(channel["state"])
            if (channel["channelPoint"] == funding_txid+":"+output_index) and (channel["state"] == "NORMAL"):
                return True
        return False

