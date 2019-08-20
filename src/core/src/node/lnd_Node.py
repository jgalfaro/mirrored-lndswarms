#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
import json
import time
import threading
import docker

from src.utils.conf import *
from src.utils.dockerUtilities import *

class lnd_Node:

    def __init__(self):
        self.id = ""
        self.container_node = None
        self.identity_pubkey = None
        self.ip_add = None
        self.pause_thread = threading.Thread(target=self.pause_when_event_occurs)
        self.pause_event_msgs = []
        #self.pause_event_from_ip = ""

    def _set_lnd_info(self):
        info_lnd_node = self.get_info(True)
        self.ip_add = self.container_node.get_container_ip_address()
        self.identity_pubkey = info_lnd_node["identity_pubkey"]
        return

    def set_container_node(self, container_node):
        self.container_node = container_node
        self._set_lnd_info()
        return

    def run_command_in_lnd(self, command, quiet=False):
        docker_utilities = DockerUtilities()

        if not docker_utilities.is_container_running(self.container_node):
            #raise SystemError("The lnd_btc container "+self.container_node.get_container_id()+" is not running")
            print("The lnd_btc container " + self.container_node.get_container_id() + " is not running")
            # Try to restart container
            docker_utilities.restart_container(self.container_node)

        success, output = docker_utilities.run_docker_command(self.container_node, command)
        if not success:
            print 'There was an error executing command: '+command+', in container: '+self.container_node.get_container_name()
        if not quiet:
            print "$ "+command
            print output
        return output

    def run_lncli_command(self, lncli_command, quiet=False):
        output = self.run_command_in_lnd(LND_COMMAND_PREFIX+lncli_command, quiet)
        try:
            output = json.loads(output)
        except ValueError as ve:
            print "Not JSON can be decoded from the output of command:"+LND_COMMAND_PREFIX+lncli_command
        return output

    def pause_when_event_occurs(self):
        docker_utilities = DockerUtilities()

        if not docker_utilities.is_container_running(self.container_node):
            # raise SystemError("The lnd_btc container "+self.container_node.get_container_id()+" is not running")
            print("The lnd_btc container " + self.container_node.get_container_id() + " is not running")
            # Try to restart container
            docker_utilities.restart_container(self.container_node)

        print "Pause node thread initialized!!!!"
        print "Node will be paused when the following messages appears in 1 line of the logs: "
        print self.pause_event_msgs
        docker_container = docker_utilities.docker_client.containers.get(self.container_node.get_container_id())

        for line in docker_container.logs(stream=True):
            if all(msg in line for msg in self.pause_event_msgs):
                print "*" * 100
                print "Pause event found in the following line of log:"
                print line
                print "*" * 100
                print "Pausing node: " + self.identity_pubkey
                print "*" * 100
                try:
                    docker_container.pause()
                except docker.errors.APIError:
                    print "Error pausing node!!!"
                    exit(1)
                return

    def unpause_node(self):
        docker_utilities = DockerUtilities()

        if not docker_utilities.is_container_paused(self.container_node):
            # Container is not paused
            if docker_utilities.is_container_running(self.container_node):
                return True
            else:
                return False

        docker_container = docker_utilities.docker_client.containers.get(self.container_node.get_container_id())
        try:
            docker_container.unpause()
            return True
        except docker.errors.APIError:
            print "Error unpausing node!!!"
            exit(1)
        return False

    def is_node_synced_to_chain(self):
        return self.is_lnd_synced_to_chain()

    def is_lnd_synced_to_chain(self):
        for i in range(6):
            output = self.run_command_in_lnd(LND_COMMAND_PREFIX + "getinfo", True)
            lnd_node_info = None
            try:
                lnd_node_info = json.loads(output)
            except ValueError as ve:
                pass
            if not lnd_node_info:
                print "- Warning: LND daemon is not active yet, waiting 5 seconds"
            else:
                if not lnd_node_info["synced_to_chain"] and lnd_node_info["block_height"] != 0:
                    print "- Warning: LND node is not synced to chain, waiting 5 seconds"
                else:
                    # LND node is synced to chain
                    return
            time.sleep(5)

        print "LND node was not able to synchronize to chain!"
        exit(1)

    def is_lnd_daemon_active(self):
        for i in range(6):
            output = self.run_command_in_lnd(LND_COMMAND_PREFIX + "getinfo", True)
            lnd_node_info = None
            try:
                lnd_node_info = json.loads(output)
            except ValueError as ve:
                pass
            if not lnd_node_info:
                print "- Warning: LND daemon is not active yet, waiting 5 seconds"
            else:
                return
            time.sleep(5)

        print "LND was not active after waiting time!"
        exit(1)

    def get_info(self, quiet=False):
        self.is_lnd_daemon_active()
        return self.run_lncli_command("getinfo", quiet)

    def new_address(self, type="np2wkh", quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("newaddress "+type, quiet)

    def channel_balance(self, funding_txid, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        output =  self.run_lncli_command("listchannels", True)
        for chan in output["channels"]:
            if funding_txid in chan["channel_point"]:
                print json.dumps(chan, indent=1)
                return chan

    def wallet_balance(self, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("walletbalance", quiet)

    def list_peers(self, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("listpeers", quiet)

    def list_channels(self, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("listchannels", quiet)

    def connect_to_node(self, identity_pubkey, ip_addr, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("connect "+identity_pubkey+"@"+ip_addr, quiet)

    def disconnect_from_node(self, identity_pubkey, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("disconnect "+identity_pubkey, quiet)

    def open_channel(self, identity_pubkey, local_amount, quiet=False):
        docker_utils = DockerUtilities()
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        output = self.run_lncli_command("openchannel --node_key="+identity_pubkey+" --local_amt="+str(local_amount), quiet)
        channel_funtxid = output["funding_txid"]

        channel_output_index = ""
        for j in range(1, 40, 5):
            bitcoind_container = docker_utils.docker_client.containers.get(BLOCKCHAIN_CONTAINER_NAME)
            bitcoind_container.exec_run(BLOCKCHAIN_COMMAND_PREFIX + "generate "+str(j))
            cmd_out = self.list_channels(True)
            for channel in cmd_out["channels"]:
                if (channel_funtxid in channel["channel_point"]) and (channel["active"]):
                    channel_output_index = channel["channel_point"].split(':')[1]
                    break
            if channel_output_index is not "":
                break
            time.sleep(5)

        channel_output_index = "0" if channel_output_index is "" else channel_output_index
        print "- Generated " + str(j) + " block so the channel is confirmed and active:"
        return channel_funtxid, channel_output_index

    def close_channel(self, funding_txid, output_index, quiet=False):
        docker_utils = DockerUtilities()
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        output = self.run_lncli_command("closechannel --funding_txid="+funding_txid+ " --output_index="+output_index, quiet)
        # Wait till unconfirmed fund are treated
        for j in range(1, 40, 5):
            bitcoind_container = docker_utils.docker_client.containers.get(BLOCKCHAIN_CONTAINER_NAME)
            bitcoind_container.exec_run(BLOCKCHAIN_COMMAND_PREFIX + "generate "+str(j))
            cmd_out = self.wallet_balance(True)
            if int(cmd_out["unconfirmed_balance"]) == 0:
                break
            time.sleep(5)

        if int(cmd_out["unconfirmed_balance"]) != 0:
            print "- After " + str(j) + " blocks generated the funds could not be confirmed on the channel"
            exit(1)

        print "- Generated " + str(j) + " block so the channel is closed and funds are confirmed"
        return output

    def get_channel_and_peer_id(self, funding_txid):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        list_channels = self.list_channels(True)
        peer_channel_id = ""
        peer_id = ""
        for channel in list_channels["channels"]:
            if funding_txid in channel["channel_point"]:
                peer_channel_id = channel["chan_id"]
                peer_id = channel["remote_pubkey"]
                break

        if peer_channel_id == "":
            print "Error getting Channel ID from funding_txid: "+funding_txid
            exit(1)

        return peer_channel_id, peer_id

    def add_invoice(self, amount, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        json_output = self.run_lncli_command("addinvoice --amt="+str(amount), quiet)
        return json_output["pay_req"]

    def send_payment(self, payment_request, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("sendpayment --pay_req="+payment_request+" --force", quiet)

    def send_to_route(self, payment_hash, routes, retries=6, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        # Escape the quote characters by doubling the json.dumps over the given dictionary of routes
        json_routes = json.dumps(json.dumps(routes))
        self.run_command_in_lnd("sh -c 'echo \"" + json_routes + "\" > /tmp/routes'", quiet=True)
        for i in range(retries):
            json_output = None
            self.is_lnd_synced_to_chain()
            try:
                out_put = self.run_command_in_lnd(
                    "sh -c 'cat /tmp/routes | " + LND_COMMAND_PREFIX + "sendtoroute --payment_hash=" + payment_hash + " -'",
                    True)
                json_output = json.loads(out_put)
            except ValueError as ve:
                print "Not JSON can be decoded from the output:"
                print out_put

            if type(json_output) is dict:
                if not quiet:
                    print json.dumps(json_output, indent=4)
                if not json_output["payment_error"]:
                    break
            print "There was an error sending the payment, retrying!\n"
            time.sleep(5)
        return json_output

    def query_routes(self, identity_pubkey, amount, quiet=False):
        for i in range(6):
            # First check synchronization to chain
            self.is_lnd_synced_to_chain()
            json_output = self.run_lncli_command("queryroutes --dest=" + identity_pubkey + " --amt="+str(amount), True)
            if type(json_output) is dict:
                if not quiet:
                    print json.dumps(json_output, indent=4)
                break
            time.sleep(5)
        return json_output

    def decode_payment_request(self, payment_request, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("decodepayreq " + payment_request, quiet)

    def get_expiry_and_fees_from_channel(self, channel_id, node_id, quiet=False):
        for i in range(6):
            # First check synchronization to chain
            self.is_lnd_synced_to_chain()
            json_output = self.run_lncli_command("getchaninfo  " + channel_id, quiet)
            if json_output["node1_policy"] and json_output["node2_policy"]:
                if not quiet:
                    print json.dumps(json_output, indent=4)
                break
            time.sleep(5)

        expiry = None
        fee_base_msat = None
        fee_rate_milli_msat = None

        if json_output["node1_pub"] == node_id:
            expiry = json_output["node1_policy"]["time_lock_delta"]
            fee_base_msat = json_output["node1_policy"]["fee_base_msat"]
            fee_rate_milli_msat = json_output["node1_policy"]["fee_rate_milli_msat"]

        elif json_output["node2_pub"] == node_id:
            expiry = json_output["node2_policy"]["time_lock_delta"]
            fee_base_msat = json_output["node2_policy"]["fee_base_msat"]
            fee_rate_milli_msat = json_output["node2_policy"]["fee_rate_milli_msat"]

        return int(expiry), int(fee_base_msat), int(fee_rate_milli_msat)

    def is_channel_active(self, funtxid, output_index):
        cmd_out = self.list_channels(True)
        for channel in cmd_out["channels"]:
            print "Channel active value: " + str(channel["active"])
            if (funtxid in channel["channel_point"]) and (channel["active"]):
                return True
        return False

    def is_block_height_ok(self, block_count):
        # Check if the node has the same block count as the one passed as a parameter
        for i in range(6):
            node_info = self.get_info(True)
            if type(node_info) is dict:
                if node_info["block_height"] == block_count:
                    return True
            time.sleep(5)
        return False
