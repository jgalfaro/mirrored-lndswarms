#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
from dockerUtilities import *
from conf import *
from dockerUtilities import *
import json
import time


class lnd_Node:

    def __init__(self):
        self.id = ""
        self.container_node = None
        self.identity_pubkey = None
        self.ip_add = None

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

        if docker_utilities.is_container_running(self.container_node):
            raise SystemError("The lnd_btc container "+self.container_node.get_container_id()+" is not running")

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
                if not lnd_node_info["synced_to_chain"]:
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

    def channel_balance(self, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("channelbalance", quiet)

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

    def open_channel(self, identity_pubkey, local_amount, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("openchannel --node_key="+identity_pubkey+" --local_amt="+str(local_amount), quiet)

    def close_channel(self, funding_txid, output_index, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("closechannel --funding_txid="+funding_txid+ " --output_index="+output_index, quiet)

    def add_invoice(self, amount, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        json_output = self.run_lncli_command("addinvoice --amt="+str(amount), quiet)
        return json_output["pay_req"]

    def send_payment(self, payment_request, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("sendpayment --pay_req="+payment_request+" --force", quiet)

    def send_to_route(self, payment_hash, routes, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("sendtoroute --payment_hash="+payment_hash+" --routes="+routes, quiet)

    def query_routes(self, identity_pubkey, amount, quiet=False):
        # First check synchronization to chain
        self.is_lnd_synced_to_chain()
        return self.run_lncli_command("queryroutes --dest=" + identity_pubkey + " --amt="+amount, quiet)

    def is_channel_active(self, funtxid, output_index):
        cmd_out = self.list_channels(True)
        for channel in cmd_out["channels"]:
            print "Channel active value: " + str(channel["active"])
            if (funtxid in channel["channel_point"]) and (channel["active"]):
                return True
        return False

