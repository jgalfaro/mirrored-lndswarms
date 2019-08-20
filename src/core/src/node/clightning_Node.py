#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
import json
import time

from src.utils.conf import *
from src.utils.dockerUtilities import *

class clightning_Node:

    def __init__(self):
        self.id = ""
        self.container_node = None
        self.identity_pubkey = None
        self.ip_add = None

    def _set_clightning_info(self):
        info_node = self.get_info(True)
        self.ip_add = self.container_node.get_container_ip_address()
        self.identity_pubkey = info_node["id"]
        return

    def set_container_node(self, container_node):
        self.container_node = container_node
        self._set_clightning_info()
        return

    def check_if_log_has_list_of_messages(self, list_msg):
        docker_utilities = DockerUtilities()

        if not docker_utilities.is_container_running(self.container_node):
            # raise SystemError("The lnd_btc container "+self.container_node.get_container_id()+" is not running")
            print("The clightning container " + self.container_node.get_container_id() + " is not running")
            # Try to restart container
            docker_utilities.restart_container(self.container_node)

        print "Checking if node has the following messages on its logs:"
        print list_msg

        docker_container = docker_utilities.docker_client.containers.get(self.container_node.get_container_id())
        # Check logs from last 2 minutes
        epoch_time = int(time.time()) - 120
        logs = docker_container.logs(since=epoch_time)
        for line in logs.splitlines():
            if all(msg in line for msg in list_msg):
                print "Messages found on the following line of log:"
                print line
                return True
        return False

    def run_command_in_clightning(self, command, quiet=False):
        docker_utilities = DockerUtilities()

        if not docker_utilities.is_container_running(self.container_node):
            #raise SystemError("The clightning_btc container "+self.container_node.get_container_id()+" is not running")
            print("The clightning_btc container " + self.container_node.get_container_id() + " is not running")
            # Try to restart container
            docker_utilities.restart_container(self.container_node)

        success, output = docker_utilities.run_docker_command(self.container_node, command)
        if not success:
            print 'There was an error executing command: '+command+', in container: '+self.container_node.get_container_name()
        if not quiet:
            print "$ "+command
            print output
        return output

    def run_cli_command(self, command, quiet=False):
        output = self.run_command_in_clightning(CLIGHTNING_COMMAND_PREFIX+command, quiet)
        try:
            output = json.loads(output)
        except ValueError as ve:
            print "Not JSON can be decoded from the output of command:" + CLIGHTNING_COMMAND_PREFIX + command
        return output

    def is_lightning_daemon_active(self):
        docker_utilities = DockerUtilities()

        for i in range(6):
            output = self.run_command_in_clightning(CLIGHTNING_COMMAND_PREFIX + "getinfo", True)
            node_info = None
            try:
                node_info = json.loads(output)
            except ValueError as ve:
                pass
            if not node_info:
                print "- Warning: Lightning daemon is not active yet, waiting 5 seconds"
            else:
                return
            time.sleep(5)

        print "Lightning daemon was not active after waiting time!"
        print "Trying to restart container: "+self.container_node.get_container_name()
        docker_utilities.restart_container(self.container_node)

    def is_node_synced_to_chain(self):
        return self.is_clightning_synced_to_chain()

    def is_clightning_synced_to_chain(self):
        docker_utils = DockerUtilities()
        retries = 20
        for i in range(retries):
            output = self.run_command_in_clightning(CLIGHTNING_COMMAND_PREFIX + "getinfo", True)
            node_info = None
            try:
                node_info = json.loads(output)
            except ValueError as ve:
                pass
            if not node_info:
                print "- Warning: C-Lightning daemon is not active yet, waiting 5 seconds"
            else:
                clightning_blockheight = node_info["blockheight"]

                try:
                    bitcoind_container = docker_utils.docker_client.containers.get(BLOCKCHAIN_CONTAINER_NAME)
                    success, output = bitcoind_container.exec_run(BLOCKCHAIN_COMMAND_PREFIX+"getblockchaininfo")
                    blockchain_info = json.loads(output)
                except docker.errors.APIError as de:
                    print("Error getting blockchain info")
                except ValueError as ve:
                    print("Error getting a JSON instance from blockchain info")

                # If the block height are differents, it means that eclair is not synced:
                if blockchain_info["blocks"] != clightning_blockheight:
                    print "- Warning: C-Lightning node is not synced to chain, waiting 5 seconds"
                else:
                    # C-Lightning node is synced to chain
                    return
            time.sleep(5)

        print "C-Lightning node was not able to synchronize to chain after "+str(retries*5)+" seconds!"
        print "Restarting C-Lightning container node:"+self.container_node.get_container_name()
        if not docker_utils.restart_container(self.container_node):
            exit(1)
        # Check that daemon is active after restart
        self.is_lightning_daemon_active()
        return

    def get_info(self, quiet=False):
        self.is_lightning_daemon_active()
        return self.run_cli_command("getinfo", quiet)

    def new_address(self, type="p2sh-segwit", quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("newaddr "+type, quiet)

    def channel_balance(self, funding_txid, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        l_peer = self.list_peers(True)
        for peer in l_peer["peers"]:
            for chan in peer["channels"]:
                if funding_txid in chan["funding_txid"]:
                    print json.dumps(chan, indent=1)
                    return chan

    def wallet_balance(self, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("listfunds", quiet)

    def list_peers(self, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("listpeers", quiet)

    def list_channels(self, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("listchannels source="+self.identity_pubkey, quiet)

    def connect_to_node(self, identity_pubkey, ip_addr, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("connect "+identity_pubkey+"@"+ip_addr, quiet)

    def open_channel(self, identity_pubkey, local_amount, quiet=False):
        docker_utils = DockerUtilities()
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        open_output = self.run_cli_command("fundchannel "+identity_pubkey+" "+str(local_amount), quiet)

        channel_id = open_output["channel_id"]

        channel_funtxid = ""
        for j in range(1, 40, 5):
            bitcoind_container = docker_utils.docker_client.containers.get(BLOCKCHAIN_CONTAINER_NAME)
            bitcoind_container.exec_run(BLOCKCHAIN_COMMAND_PREFIX + "generate "+str(j))
            l_peers = self.run_cli_command("listpeers",True)
            for peer in l_peers["peers"]:
                for channel in peer["channels"]:
                    if (channel_id in channel["channel_id"]) and (channel["state"] == "CHANNELD_NORMAL"):
                        channel_funtxid = channel["funding_txid"]
                        break
                if channel_funtxid is not "":
                    break
            time.sleep(5)

        print "- Generated " + str(j) + " block so the channel is confirmed and active:"
        return channel_funtxid, '0'

    def close_channel(self, funding_txid, output_index, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        # We cant close the channel directly using the funding_txid, we have to look at the list of peers and look
        # in their channels list to obtain the peer_channel_id or peer_id
        peer_channel_id, peer_id = self.get_channel_and_peer_id(funding_txid)

        # Now close the channel
        output = self.run_cli_command("close "+peer_channel_id, quiet)

        # Wait till unconfirmed funds are treated
        funds_confirmed = False
        for j in range(1, 40, 5) and not funds_confirmed:
            bitcoind_container = docker_utils.docker_client.containers.get(BLOCKCHAIN_CONTAINER_NAME)
            bitcoind_container.exec_run(BLOCKCHAIN_COMMAND_PREFIX + "generate " + str(j))
            l_peers = self.list_peers(True)
            for peer in l_peers["peers"] and not funds_confirmed:
                for channel in peer["channels"]:
                    if peer_channel_id in channel["channel_id"]:
                        if (channel["in_payments_offered"] == channel["in_payments_fulfilled"]) and (channel["out_payments_offered"] == channel["out_payments_fulfilled"]):
                            funds_confirmed = True
                            break
            time.sleep(5)

        if not funds_confirmed:
            print "- After " + str(j) + " blocks generated the funds could not be confirmed on the channel"
            exit(1)

        print "- Generated " + str(j) + " block so the channel is closed and funds are confirmed"
        return output

    def get_channel_and_peer_id(self, funding_txid):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        peers = self.list_peers(True)
        peer_channel_id = ""
        for peer in peers:
            peer_id = peer["id"]
            for channel in peer["channels"]:
                if funding_txid == channel["funding_txid"]:
                    peer_channel_id = channel["channel_id"]
                    break
            if peer_channel_id != "":
                break
        if peer_channel_id == "":
            print "Error getting Channel ID from funding_txid: "+funding_txid
            exit(1)

        return peer_channel_id, peer_id

    def add_invoice(self, amount, label="label_", desc="desc_",quiet=False):
        """
        Create a Lightning invoice using C-Lightning command line interface
        :param amount: Amount of the invoice in Satoshis
        :param label: Label for the invoice
        :param desc: Description of the invoice
        :return JSON object with the output of the command
        """
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        date_string = str(time.time()).strip('.')
        # Since the amount expected is in Satoshis and the invoice command in C-Lightning expects Msatoshis we multiply
        # amount by 1000
        json_output = self.run_cli_command("invoice "+str(amount*1000)+" "+label+date_string+" "+desc+date_string, quiet)
        return json_output["bolt11"]

    def send_payment(self, payment_request, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("pay "+payment_request, quiet)

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
        self.is_clightning_synced_to_chain()

        # Let's check the format of channel_id:
        try:
            channel_id = int(channel_id)
            # Is LND format, change format to Short ID used by C-Lightning
            block, tx, output = self._lnd_chan_id_to_short_id(channel_id)
            channel_id = str(block)+'x'+str(tx)+'x'+str(output)
        except ValueError:
            # Is not a valid integer, check if it comes with a 'x'
            if 'x' in channel_id:
                # It has short ID format, no need to change
                pass

        expiry = None
        fee_base_msat = None
        fee_rate_milli_msat = None

        # Lets get channel info for channel with id channel_id with source node_id
        json_output = self.run_cli_command("listchannels "+channel_id, True)

        for channel in json_output["channels"]:
            if channel["source"] == node_id:
                fee_rate_milli_msat = channel["fee_per_millionth"]
                fee_base_msat = channel["base_fee_millisatoshi"]
                expiry = channel["delay"]

        return int(expiry), int(fee_base_msat), int(fee_rate_milli_msat)

    def is_channel_active(self, funtxid, output_index):
        cmd_out = self.list_peers(True)
        for peer in cmd_out["peers"]:
            for channel in peer["channels"]:
                print "Channel active value: " + str(channel["state"])
                if (funtxid in channel["funding_txid"]) and (channel["state"] == "CHANNELD_NORMAL"):
                    return True
        return False

    def is_block_height_ok(self, block_count):
        # Check if the node has the same block count as the one passed as a parameter
        for i in range(6):
            node_info = self.get_info(True)
            if type(node_info) is dict:
                if node_info["blockheight"] == block_count:
                    return True
            time.sleep(5)
        return False

