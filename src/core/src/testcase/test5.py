#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
import time
import json

from src.controller.bitcoindController import *
from src.controller.lnd_btcController import *
from src.controller.clightning_btcController import *
from src.controller.eclair_btcController import *
from src.utils.conf import *

src_begin = "\n#+BEGIN_SRC bash"
src_end = "#+END_SRC\n"


# Names of Nodes of the testbed
lnd_nodes_name = {0: {'topo_name': "M"}, 1: {'topo_name': "B_i"}}
eclair_nodes_name = {0: {'topo_name': "B_j"}}
clightning_nodes_name = {0: {'topo_name': "B_k"}}


def get_hop_fee_msat(fee_base_msat, amount_to_forward_msat, fee_rate_milli_msat):
    # Calcutate fees in msat as follows:
    # fee_base_msat + (amount_to_forward_msat * fee_rate_msat / 1000000)
    return int(float(fee_base_msat) + (float(amount_to_forward_msat) * (float(fee_rate_milli_msat) / float(1000000))))


def get_node_name_and_type(identity_pubkey):
    node_type = ""
    node_name = ""
    if identity_pubkey in lnd_nodes_name:
        node_type = "LND"
        node_name = lnd_nodes_name[identity_pubkey]["topo_name"]
    elif identity_pubkey in clightning_nodes_name:
        node_type = "C-Lightning"
        node_name = clightning_nodes_name[identity_pubkey]["topo_name"]
    elif identity_pubkey in eclair_nodes_name:
        node_type = "Eclair"
        node_name = eclair_nodes_name[identity_pubkey]["topo_name"]
    return node_name, node_type


def init_test():
    print '----- Starting Test 5 -----'

    bitcoind = bitcoindController()
    blockchain = bitcoind.bitcoind_node
    lnd = lnd_btcController(len(lnd_nodes_name))
    clight = clightning_btcController(len(clightning_nodes_name))
    eclair = eclair_btcController(len(eclair_nodes_name))

    # Test variables
    BLOCKS_TO_GENERATE = 500
    MIN_BTC_FUNDS_TO_SEND = 10
    CHAN_VALUE = 930900
    INVOICE_DEBIT = 100000
    ROUTE_PAYMENT_AMOUNT = 40000

    testbed_nodes = []
    if len(lnd.lnd_nodes) < len(lnd_nodes_name):
        print "Not enough LND nodes needed " + str(len(lnd_nodes_name)) + ", only " + str(len(lnd.lnd_nodes))
        exit(1)
    if len(clight.clightning_nodes) < len(clightning_nodes_name):
        print "Not enough C-Lightning nodes needed " + str(len(clightning_nodes_name)) + ", only " + str(
            len(clight.clightning_nodes))
        exit(1)
    if len(eclair.eclair_nodes) < len(eclair_nodes_name):
        print "Not enough Eclair nodes needed " + str(len(eclair_nodes_name)) + ", only " + str(
            len(eclair.eclair_nodes))
        exit(1)

    if not blockchain:
        print "There is not a Bitcoin-core instance running!"
        exit(1)

    print "## LND nodes information "
    for i in range(len(lnd_nodes_name)):
        print "- Node " + lnd_nodes_name[i]['topo_name'] + " IP address: " + lnd.lnd_nodes[i].ip_add
        print "- Node " + lnd_nodes_name[i]['topo_name'] + " ID: " + lnd.lnd_nodes[i].identity_pubkey

        # We change default key of dictionary with the identity pubkey of the Node. Later we can find easier the node
        # by its pub_key
        lnd_nodes_name[lnd.lnd_nodes[i].identity_pubkey] = lnd_nodes_name.pop(i)
        # Append the LND nodes to the list of testbed nodes
        testbed_nodes.append(lnd.lnd_nodes[i])

    print "## Eclair nodes information "
    for i in range(len(eclair_nodes_name)):
        print "- Node " + eclair_nodes_name[i]['topo_name'] + " IP address: " + eclair.eclair_nodes[i].ip_add
        print "- Node " + eclair_nodes_name[i]['topo_name'] + " ID: " + eclair.eclair_nodes[i].identity_pubkey
        # We change default key of dictionary with the identity pubkey of the Node. Later we can find easier the node
        # by its pub_key
        eclair_nodes_name[eclair.eclair_nodes[i].identity_pubkey] = eclair_nodes_name.pop(i)
        # Append the eclair_nodes to the list of testbed nodes
        testbed_nodes.append(eclair.eclair_nodes[i])

    print "## C-Lightning nodes information "
    for i in range(len(clightning_nodes_name)):
        print "- Node " + clightning_nodes_name[i]['topo_name'] + " IP address: " + clight.clightning_nodes[i].ip_add
        print "- Node " + clightning_nodes_name[i]['topo_name'] + " ID: " + clight.clightning_nodes[i].identity_pubkey
        # We change default key of dictionary with the identity pubkey of the Node. Later we can find easier the node
        # by its pub_key
        clightning_nodes_name[clight.clightning_nodes[i].identity_pubkey] = clightning_nodes_name.pop(i)
        # Append the clightning_nodes to the list of testbed nodes
        testbed_nodes.append(clight.clightning_nodes[i])

    print "## "+str(BLOCKS_TO_GENERATE)+" Blocks generation on bitcoin-core (at least 432 to activate segwit?):"
    print src_begin
    blockchain.generate_blocks(BLOCKS_TO_GENERATE)
    print src_end

    print '## Blockchain info and segwit activation verification:'
    print src_begin
    blockchain.get_blockchain_info()
    print src_end

    # Create address and send funds to each testbed node so they can create channels
    print "** Create address and send funds to M node so it can create channels"
    print src_begin
    cmd_out = testbed_nodes[0].new_address()
    print src_end

    curr_addr = cmd_out["address"]
    print "## M address is: " + curr_addr

    print "## Send funds to M (" + str(MIN_BTC_FUNDS_TO_SEND) + "):"
    print src_begin
    blockchain.send_funds_to_address(curr_addr, MIN_BTC_FUNDS_TO_SEND)
    print src_end

    print "## Generate 1 block so the funds can be confirmed to M :"
    print src_begin
    blockchain.generate_blocks(1)
    print src_end

    print "## Get M wallet balance:"
    print src_begin
    testbed_nodes[0].wallet_balance()
    print src_end

    # Create channel from M and send funds to the rest of nodes
    M_node = testbed_nodes[0] # Node M
    M_node_name, M_node_type = get_node_name_and_type(M_node.identity_pubkey)
    for node in testbed_nodes[1:]:
        next_node_name, next_node_type = get_node_name_and_type(node.identity_pubkey)
        # Create channels from the M to the next one
        print "## Connect " + M_node_name + " (" + M_node_type + ") to " + next_node_name + " (" + next_node_type + ")"
        print src_begin
        M_node.connect_to_node(node.identity_pubkey, node.ip_add)
        print src_end

        print "## Open channel from " + M_node_name + " to " + next_node_name + " with " + str(
            CHAN_VALUE) + " satoshis:"
        print src_begin
        channel_funtxid, channel_output_index = M_node.open_channel(node.identity_pubkey, CHAN_VALUE)
        print "- " + next_node_name + " <-> " + M_node_name + " Channel funtxid: " + channel_funtxid + ", Channel output index: " + channel_output_index

        print src_end

        print "## Create an invoice at node " + next_node_name + " for " + str(CHAN_VALUE-INVOICE_DEBIT) + " Sathoshis:"
        print src_begin
        pay_req = node.add_invoice(CHAN_VALUE-INVOICE_DEBIT)
        print src_end

        print "## Send payment from node " + M_node_name + " and check balance:"
        print src_begin
        output = M_node.send_payment(pay_req)

        # Check if they were problems sending the payment
        retries = 0
        while retries < 5:
            if "unable to find a path to destination" in output:
                print '-- There was an error sending the payment, retry sending again:'
                # The errror might come from not enough blocks to activate the channel
                blockchain.generate_blocks(6, True)
                time.sleep(5)
                if M_node.is_channel_active(channel_funtxid, channel_output_index):
                    # Retry payment
                    print src_begin
                    output = M_node.send_payment(pay_req)
                    print src_end
            else:
                break
            retries = retries + 1
        print src_end

        print "##  Check channel balance info on " + M_node_name
        print src_begin
        M_node.channel_balance(channel_funtxid)
        print src_end

        print "##  Check channel balance info on " + next_node_name
        print src_begin
        node.channel_balance(channel_funtxid)
        print src_end

        print "##  Close channel from M so the funds are confirmed on " + next_node_name
        print src_begin
        M_node.close_channel(channel_funtxid, channel_output_index)
        blockchain.generate_blocks(1)
        print src_end

        print "##  Check wallet balance info on " + M_node_name
        print src_begin
        M_node.wallet_balance()
        print src_end

        print "##  Check wallet balance info on " + next_node_name
        print src_begin
        node.wallet_balance()
        print src_end

        print "## Disconnect M from node " + next_node_name
        print src_begin
        M_node.disconnect_from_node(node.identity_pubkey)
        print src_end

    # --------------------------------------------------------------------------------
    # Create channels from M - Bi - Bj - Bk - M
    i = 0
    print "** Create channels from M - Bi - Bj - Bk - M"
    prev_node = M_node
    channel_nodes = testbed_nodes[1:]
    channel_nodes.append(M_node)
    for node in channel_nodes:
        prev_node_name, prev_node_type = get_node_name_and_type(prev_node.identity_pubkey)
        next_node_name, next_node_type = get_node_name_and_type(node.identity_pubkey)

        # Create channels from the prev node to the next one
        print "## Connect "+prev_node_name+" ("+prev_node_type+") to "+next_node_name+" ("+next_node_type+")"
        print src_begin
        prev_node.connect_to_node(node.identity_pubkey, node.ip_add)
        print src_end

        print "## Open channel from "+prev_node_name+" to "+next_node_name+" with " + str(CHAN_VALUE-INVOICE_DEBIT*2) + " satoshis:"
        print src_begin
        channel_funtxid, channel_output_index = prev_node.open_channel(node.identity_pubkey, CHAN_VALUE-INVOICE_DEBIT*2)

        print "- "+next_node_name+" <-> "+prev_node_name+ str(
            i) + " Channel funtxid: " + channel_funtxid + ", Channel output index: " + channel_output_index

        print src_end

        print "## Create an invoice at node "+next_node_name+" for " + str(INVOICE_DEBIT*2) + " Sathoshis:"
        print src_begin
        pay_req = node.add_invoice(INVOICE_DEBIT*2)
        print src_end

        print "## Send payment from node "+prev_node_name+" and check balance:"
        print src_begin
        output = prev_node.send_payment(pay_req)

        # Check if they were problems sending the payment
        retries = 0
        while retries < 5:
            if "unable to find a path to destination" in output:
                print '-- There was an error sending the payment, retry sending again:'
                # The errror might come from not enough blocks to activate the channel
                blockchain.generate_blocks(6, True)
                time.sleep(5)
                if prev_node.is_channel_active(channel_funtxid, channel_output_index):
                    # Retry payment
                    print src_begin
                    output = prev_node.send_payment(pay_req)
                    print src_end
            else:
                break
            retries = retries + 1
        print src_end

        print "##  Check channel balance info on "+prev_node_name
        print src_begin
        prev_node.channel_balance(channel_funtxid)
        print src_end

        print "##  Check channel balance info on "+next_node_name
        print src_begin
        node.channel_balance(channel_funtxid)
        print src_end
        prev_node = node

    # -----------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------
    # Create a payment from M that goes through a cyclic route back to itself
    print "## Create an invoice at node M for " + str(ROUTE_PAYMENT_AMOUNT) + " Sathoshis:"
    print src_begin
    pay_req = M_node.add_invoice(ROUTE_PAYMENT_AMOUNT)
    print src_end
    # Get decoded information from previous pay_req
    decoded_pay_req = lnd.lnd_nodes[0].decode_payment_request(pay_req,True)
    payment_hash = decoded_pay_req["payment_hash"]
    #blockchain.generate_blocks(1, True)

    # Build the initial steps of the cyclic route: M - Bi - Bj - Bk - M
    # Get route from M to Bk
    print "## Creating cyclic route M - Bi - Bj - Bk - M"
    retries = 5
    for i in range(retries):
        routes = M_node.query_routes(testbed_nodes[-1].identity_pubkey, ROUTE_PAYMENT_AMOUNT, True)
        #print M_node.query_routes(testbed_nodes[-1].identity_pubkey, ROUTE_PAYMENT_AMOUNT)["routes"][0]["hops"][0]

        # At this point the query routes command should give us 2 routes:
        # - Route from M to Bk with 1 hop using channel M <-> Bk directly
        # - Route from M to Bk with 3 hops using channels M <-> Bi <-> Bj <-> Bk

        final_hop = None
        big_route = None
        for route in routes["routes"]:
            if len(route["hops"]) == 1:
                # Save route with 1 hop
                final_hop = route["hops"][0]
            elif len(route["hops"]) == 3:
                # Save the long route
                big_route = route

        if (final_hop is not None) and (big_route is not None):
            # Change final_hop to be node M
            final_hop["pub_key"] = M_node.identity_pubkey
            # Append final hop to big route hops
            big_route["hops"].append(final_hop)
            print "Initial hops to cyclic route found"
            break
        time.sleep(5)

    if i >= retries-1:
        print "No valid routes found from query routes command"
        exit(1)

    # Calculate delta_p based on the Tmax values for each implementation
    tmax_lnd = 5000
    tmax_clightning = 2016
    tmax_eclair = 1008

    delta_p = 5001
    expiry_sum = 0
    dict_hop_info = {}
    print "** Delta p Calculation"
    for hop in big_route["hops"][:-1]:
        hop_id = hop["pub_key"]
        hop_chanid = hop["chan_id"]
        hop_name, hop_type = get_node_name_and_type(hop_id)
        tmax_impl = 0

        # Get expiry_delta for each implementation
        if hop_type == "LND":
            tmax_impl = tmax_lnd
            expiry_delta, fee_base_msat, fee_rate_milli_msat = lnd.lnd_nodes[1].get_expiry_and_fees_from_channel(
                hop_chanid,
                hop_id,
                True)
        elif hop_type == "C-Lightning":
            tmax_impl = tmax_clightning
            expiry_delta, fee_base_msat, fee_rate_milli_msat = clight.clightning_nodes[0].get_expiry_and_fees_from_channel(
                hop_chanid,
                hop_id)
        else:
            tmax_impl = tmax_eclair
            expiry_delta, fee_base_msat, fee_rate_milli_msat = eclair.eclair_nodes[0].get_expiry_and_fees_from_channel(
                hop_chanid,
                hop_id)

        print "- Current hop type is: "+hop_type+", has expiry value of: "+str(expiry_delta) + " ,for its channels"

        if delta_p > tmax_impl:
            delta_p = tmax_impl - expiry_delta
        else:
            delta_p = delta_p - expiry_delta

        print "- Delta P is then: "+str(delta_p)
        expiry_sum = expiry_sum + expiry_delta

        dict_hop_info[hop_id] = {"expiry":expiry_delta, "fee_base":fee_base_msat, "fee_rate":fee_rate_milli_msat}

    # timelock for cyclic route will be the sum of all the hops expirys  + delta_p + the current blockchain height
    total_timelock = expiry_sum + delta_p + blockchain.get_blockchain_block_count()

    # Initial expiry is the sum of a delta p value + the number of blocks in the blockchain
    b_count_before_cyclic_route = blockchain.get_blockchain_block_count()
    hop_expiry = delta_p + b_count_before_cyclic_route
    final_hop["expiry"] = hop_expiry
    # Get the amount to be forwarded to the final node
    prev_amt_to_forward_msat = int(final_hop["amt_to_forward_msat"])
    expiry_delta = 0
    prev_fee_msat = 0
    total_fees_msat = 0
    new_hops = []
    num_hops = len(big_route["hops"])
    # Start checking hops in a decreasing order from 1 node before M
    for i in range(num_hops-1)[::-1]:
        hop = big_route["hops"][i]
        hop_id = hop["pub_key"]

        # Expiry for current hop will take into account the values of previous hops
        hop_expiry = hop_expiry + expiry_delta

        # Update expiry value of current hop
        hop["expiry"] = hop_expiry

        # Get amounts to forward and fees
        amt_to_forward_msat = prev_amt_to_forward_msat + prev_fee_msat
        hop["amt_to_forward"] = str(int(amt_to_forward_msat / 1000))
        hop["amt_to_forward_msat"] = str(amt_to_forward_msat)

        # We already collected the expiry, and fees rates values from the previous delta p calculation
        expiry_delta = dict_hop_info[hop_id]["expiry"]
        fee_base_msat = dict_hop_info[hop_id]["fee_base"]
        fee_rate_milli_msat = dict_hop_info[hop_id]["fee_rate"]

        # Get fee_msat
        fee_msat = get_hop_fee_msat(fee_base_msat, amt_to_forward_msat, fee_rate_milli_msat)
        hop["fee_msat"] = str(fee_msat)
        hop["fee"] = str(int(fee_msat / 1000))
        new_hops.insert(0, hop)

        # Set values to be used by the next hop
        prev_amt_to_forward_msat = amt_to_forward_msat
        prev_fee_msat = fee_msat
        total_fees_msat = total_fees_msat + fee_msat

    # Append to new hops the final hop node M
    new_hops.append(final_hop)
    # Final Timelock and fees
    cyclic_route = {}
    cyclic_route["total_time_lock"] = hop_expiry + expiry_delta
    cyclic_route["total_fees"] = str(int(total_fees_msat / 1000))
    cyclic_route["total_fees_msat"] = str(total_fees_msat)
    total_amt_msat = ROUTE_PAYMENT_AMOUNT * 1000 + total_fees_msat
    cyclic_route["total_amt"] = str(int(total_amt_msat / 1000))
    cyclic_route["total_amt_msat"] = str(total_amt_msat)
    cyclic_route["hops"] = new_hops

    route_to_send = {"routes": []}
    route_to_send["routes"].append(cyclic_route)


    print "## Cyclic route to send the payment:"
    print src_begin
    print json.dumps(route_to_send, indent=4, sort_keys=True)
    print src_end

    print "## Check channel balance on M before payment on cyclic route:"
    print src_begin
    M_node.channel_balance(channel_funtxid)
    print src_end

    print "## Send payment over the cyclic route:"
    print src_begin
    # Start watchdog thread, to pause M when funds received
    # Pause M when receives the message Received RevokeAndAck
    # M_node.pause_event_msgs = ["Received RevokeAndAck"]

    # Pause M when receives the message "settling htlc" + the payment hash of the invoice created by M
    M_node.pause_event_msgs = ["settling htlc", payment_hash]

    # Pause M when receives the message "Settling invoice"
    # M_node.pause_event_msgs = ["Settling invoice"]

    # We can check the IP that wrote the message, for example "Received RevokeAndAck" from "10.10.10.6"
    # M_node.pause_event_msgs = ["Received RevokeAndAck", testbed_nodes[-1].ip_add]
    M_node.pause_thread.start()
    M_node.send_to_route(payment_hash, route_to_send, retries=1)
    print src_end
    # blockchain.generate_blocks(6, True)

    # ---------------------------------------------------------------------------------------
    # Node M should be paused at this point
    node_name, node_type = get_node_name_and_type(testbed_nodes[-1].identity_pubkey)
    print "-- Checking if node "+node_name+" ("+node_type+") is blocked"
    print src_begin
    print "## Blockchain count before sending payment over cyclic route was: "+str(b_count_before_cyclic_route)
    # List of message to check on nodes logs to see if channel is going to be closed
    list_msg = [M_node.identity_pubkey, "Peer permanent failure in CHANNELD_NORMAL", "SENT_ADD_ACK_REVOCATION", "hit deadline"]
    set_of_blocks = 300
    max_blocks_ahead_delta = 0
    while (max_blocks_ahead_delta < 10):
        b_count_now = blockchain.get_blockchain_block_count()
        print "## Blockchain count now is: " + str(b_count_now)
        b_count_to_delta = delta_p - (b_count_now - b_count_before_cyclic_route)
        print "## Blocks to reach Delta P: " + str(b_count_to_delta)
        if (b_count_to_delta <= set_of_blocks) and (b_count_to_delta > 0):
            set_of_blocks = b_count_to_delta
        elif b_count_to_delta <= 0:
            set_of_blocks = 1
            print "## We are ahead of Delta P with " + str(abs(b_count_to_delta)) + " blocks"
            max_blocks_ahead_delta = b_count_to_delta

        print "## Generating " + str(set_of_blocks) + " blocks on the blockchain"
        blockchain.generate_blocks(set_of_blocks, True)
        # Wait till node is synced to chain
        testbed_nodes[-1].is_node_synced_to_chain()
        print "## Checking node "+node_name+" logs:"
        if (testbed_nodes[-1].check_if_log_has_list_of_messages(list_msg)):
            print "## Node "+node_name+" is about to close the channel with node M!"
            break
        print "-"*100

    print src_end

    # --------------------------------------------------------------------------------------
    # If we want to unpause the M node we can do it by calling the method unpause_node
    # M_node.unpause_node()
    

if __name__ == '__main__':
    init_test()