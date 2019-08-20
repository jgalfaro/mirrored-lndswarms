#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
import json
import time

from src.utils.conf import *
from src.utils.dockerUtilities import *

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

        if not docker_utilities.is_container_running(self.container_node):
            #raise SystemError("The eclair_btc container "+self.container_node.get_container_id()+" is not running")
            print("The eclair_btc container "+self.container_node.get_container_id()+" is not running")
            # Try to restart container
            docker_utilities.restart_container(self.container_node)

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

    def is_node_synced_to_chain(self):
        return self.is_eclair_synced_to_chain()

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

    def channel_balance(self, funding_txid, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        output =  self.run_eclair_api_command("channels", True)
        for chan in output:
            if funding_txid in chan["channelPoint"]:
                print json.dumps(chan, indent=1)
                return chan

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

    def get_funtxid(self, channelid):
        return

    def connect_to_node(self, identity_pubkey, ip_addr, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        return self.run_eclair_api_command("connect "+identity_pubkey+"@"+ip_addr, quiet)

    def open_channel(self, identity_pubkey, local_amount, quiet=False):
        docker_utils = DockerUtilities()
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()
        output = self.run_eclair_api_command("open "+identity_pubkey+" "+str(local_amount), quiet)
        channel_id = (output.split(' ')[-1]).strip('\n')

        channel_funtxid = ""
        channel_output_index = ""
        for j in range(1, 40, 5):
            bitcoind_container = docker_utils.docker_client.containers.get(BLOCKCHAIN_CONTAINER_NAME)
            bitcoind_container.exec_run(BLOCKCHAIN_COMMAND_PREFIX + "generate "+str(j))
            chan_info = self.run_eclair_api_command("channel " + channel_id, True)

            if (str(channel_id) == str(chan_info["channelId"])) and (str(chan_info["state"]) == "NORMAL"):
                channel_funtxid = chan_info["channelPoint"].split(':')[0]
                channel_output_index = chan_info["channelPoint"].split(':')[1]
                break
            time.sleep(5)

        if channel_funtxid is "":
            print "Channel was not active after " + str(j) + " blocks generated"
            exit(1)
        print "- Generated " + str(j) + " block so the channel is confirmed and active:"
        return channel_funtxid, channel_output_index

    def close_channel(self, funding_txid, output_index, quiet=False):
        # First check synchronization to chain
        #self.is_eclair_synced_to_chain()
        channels = self.list_channels(True)
        for channel in channels:
            if channel["channelPoint"] == funding_txid+":"+output_index:
                return self.run_eclair_api_command("close "+channel["channelId"], quiet)

    def add_invoice(self, amount, quiet=False):
        """
        Create a Lightning invoice using Eclair command line interface
        :param amount: Amount of the invoice in Satoshis
        :return JSON object with the output of the command
        """
        # Since the amount expected is in Satoshis and the invoice command in Eclair expects MSatoshis we multiply
        # amount by 1000
        amount = amount * 1000

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

    def _lnd_chan_id_to_short_id(self, chan_id):
        chan_id = int(chan_id)
        block = chan_id >> 40
        tx = chan_id >> 16 & 0xFFFFFF
        output = chan_id & 0xFFFF
        return (block, tx, output)

    def _short_id_to_lnd_chan_id(self, chan_id):
        chan_id = str(chan_id)
        chan_id = [int(i) for i in chan_id.split('x')]
        return (chan_id[0] << 40) | (chan_id[1] << 16) | chan_id[2]

    def get_expiry_and_fees_from_channel(self, channel_id, node_id, quiet=False):
        # First check synchronization to chain
        self.is_eclair_synced_to_chain()

        # Let's check the format of channel_id:
        try:
            channel_id = int(channel_id)
            # Is LND format, change format to Short ID used by Eclair
            block, tx, output = self._lnd_chan_id_to_short_id(channel_id)
            channel_id = str(block) + 'x' + str(tx) + 'x' + str(output)
        except ValueError:
            # Is not a valid integer, check if it comes with a 'x'
            if 'x' in channel_id:
                # It has short ID format, no need to change
                pass

        expiry = None
        fee_base_msat = None
        fee_rate_milli_msat = None

        # Lets get updates info for channel with id channel_id and with source node_id
        json_output = self.run_eclair_api_command("allupdates "+ node_id, True)
        # Check from the latest to oldest
        json_output.reverse()
        for update in json_output:
            if update["shortChannelId"] == channel_id:
                fee_rate_milli_msat = update["feeProportionalMillionths"]
                fee_base_msat = update["feeBaseMsat"]
                expiry = update["cltvExpiryDelta"]
                break

        return int(expiry), int(fee_base_msat), int(fee_rate_milli_msat)

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

    def is_block_height_ok(self, block_count):
        # Check if the node has the same block count as the one passed as a parameter
        for i in range(6):
            node_info = self.get_info(True)
            if type(node_info) is dict:
                if node_info["blockHeight"] == block_count:
                    return True
            time.sleep(5)
        return False
