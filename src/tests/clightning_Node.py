#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'

#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
from dockerUtilities import *
from conf import *
from dockerUtilities import *
import json
import time


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

    def run_command_in_clightning(self, command, quiet=False):
        docker_utilities = DockerUtilities()

        if docker_utilities.is_container_running(self.container_node):
            raise SystemError("The clightning_btc container "+self.container_node.get_container_id()+" is not running")

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

    def is_clightning_synced_to_chain(self):
        """
        for i in range(6):
            output = self.run_command_in_clightning(CLIGHTNING_COMMAND_PREFIX + "getinfo", True)
            clightning_node_info = ""
            try:
                clightning_node_info = json.loads(output)
            except ValueError as ve:
                print "Error executing the command on clightning node:"
                print ve
            if not clightning_node_info["synced_to_chain"]:
                print "C-Lightning node is not synced to chain, waiting 5 seconds"
                time.sleep(5)
            else:
                return

        print "clightning node was not able to synchronize to chain!"
        exit(1)
        """
        return

    def get_info(self, quiet=False):
        self.is_lightning_daemon_active()
        return self.run_cli_command("getinfo", quiet)

    def new_address(self, type="np2wkh", quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("newaddress "+type, quiet)

    def channel_balance(self, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("listchannels source="+self.identity_pubkey, quiet)

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
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("openchannel --node_key="+identity_pubkey+" --local_amt="+str(local_amount), quiet)

    def close_channel(self, funding_txid, output_index, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("closechannel --funding_txid="+funding_txid+ " --output_index="+output_index, quiet)

    def add_invoice(self, amount, label="label_", desc="desc_",quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        date_string = str(time.time()).strip('.')
        json_output = self.run_cli_command("invoice "+str(amount)+" "+label+date_string+" "+desc+date_string, quiet)
        return json_output["bolt11"]

    def send_payment(self, payment_request, quiet=False):
        # First check synchronization to chain
        self.is_clightning_synced_to_chain()
        return self.run_cli_command("sendpayment --pay_req="+payment_request+" --force", quiet)

    def is_channel_active(self, funtxid, output_index):
        cmd_out = self.list_peers(True)
        for peer in cmd_out["peers"]:
            for channel in peer["channels"]:
                print "Channel active value: " + str(channel["state"])
                if (funtxid in channel["funding_txid"]) and (channel["state"] == "CHANNELD_NORMAL"):
                    return True
        return False
