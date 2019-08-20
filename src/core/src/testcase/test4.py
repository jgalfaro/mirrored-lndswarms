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


def get_hop_fee_msat(fee_base_msat, amount_to_forward_msat, fee_rate_milli_msat):
    # Calcutate fees in msat as follows:
    # fee_base_msat + (amount_to_forward_msat * fee_rate_msat / 1000000)
    return int(float(fee_base_msat) + (float(amount_to_forward_msat) * (float(fee_rate_milli_msat) / float(1000000))))


def init_test():
    print '----- Starting Test 4 -----'
    #
    # The topology of the test is as follows:
    #                                   -- B_i Nodes --
    #       LND Nodes (A)         | B_1 (LND Node)
    #  A <----------------------> | B_2 (C-Lightning Node)
    #       (A to B_i             | B_3 (Eclair Node)
    #   bidirectional Channel)
    #
    #

    lnd_nodes_name = {0: {'topo_name': "A"}, 1: {'topo_name': "B_1"}}
    clightning_nodes_name = {0: {'topo_name': "B_2"}}
    eclair_nodes_name = {0: {'topo_name': "B_3"}}

    bitcoind = bitcoindController()
    blockchain = bitcoind.bitcoind_node
    lnd = lnd_btcController(len(lnd_nodes_name))
    clight = clightning_btcController(len(clightning_nodes_name))
    eclair = eclair_btcController(len(clightning_nodes_name))

    # Test variables
    BLOCKS_TO_GENERATE = 500
    MIN_BTC_FUNDS_TO_SEND = 10
    M_A_CHAN_VALUE = 16777200
    A_Bi_CHAN_VALUE = 930900
    MAX_CONFIRMATION_BLKS = 40
    ROUTE_PAYMENT_AMOUNT = 40000
    LND_MAX_PAYMENT = 4294967
    MAX_HOPS = 20
    DEFAULT_EXPIRY_DELTA = 144

    bi_nodes = []
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

        # The first LND node is node A, so we append the rest of the lnd_nodes to the list of B_i nodes
        if i >= 1:
            bi_nodes.append(lnd.lnd_nodes[i])

    print "## C-Lightning nodes information "
    for i in range(len(clightning_nodes_name)):
        print "- Node " + clightning_nodes_name[i]['topo_name'] + " IP address: " + clight.clightning_nodes[i].ip_add
        print "- Node " + clightning_nodes_name[i]['topo_name'] + " ID: " + clight.clightning_nodes[i].identity_pubkey
        # We change default key of dictionary with the identity pubkey of the Node. Later we can find easier the node
        # by its pub_key
        clightning_nodes_name[clight.clightning_nodes[i].identity_pubkey] = clightning_nodes_name.pop(i)
        # Append the clightning_nodes to the list of B_i nodes
        bi_nodes.append(clight.clightning_nodes[i])

    print "## Eclair nodes information "
    for i in range(len(eclair_nodes_name)):
        print "- Node " + eclair_nodes_name[i]['topo_name'] + " IP address: " + eclair.eclair_nodes[i].ip_add
        print "- Node " + eclair_nodes_name[i]['topo_name'] + " ID: " + eclair.eclair_nodes[i].identity_pubkey
        # We change default key of dictionary with the identity pubkey of the Node. Later we can find easier the node
        # by its pub_key
        eclair_nodes_name[eclair.eclair_nodes[i].identity_pubkey] = eclair_nodes_name.pop(i)
        # Append the eclair_nodes to the list of B_i nodes
        bi_nodes.append(eclair.eclair_nodes[i])

    print "## " + str(BLOCKS_TO_GENERATE) + " Blocks generation on bitcoin-core (at least 432 to activate segwit?):"
    print src_begin
    blockchain.generate_blocks(BLOCKS_TO_GENERATE)
    print src_end

    print '## Blockchain info and segwit activation verification:'
    print src_begin
    blockchain.get_blockchain_info()
    print src_end

    print "## A should generate an address an receive some funds to be able to open the channels::"
    print src_begin
    cmd_out = lnd.lnd_nodes[0].new_address()
    A_addr = cmd_out["address"]
    print "A address is: " + A_addr
    print src_end

    print "## Send funds to A (" + str(MIN_BTC_FUNDS_TO_SEND) + "):"
    print src_begin
    blockchain.send_funds_to_address(A_addr, MIN_BTC_FUNDS_TO_SEND)
    print src_end

    print "## Generate 1 block so the funds can be confirmed to A:"
    print src_begin
    blockchain.generate_blocks(1)
    print src_end

    print "## Get A wallet balance:"
    print src_begin
    lnd.lnd_nodes[0].wallet_balance()
    print src_end

    # "----------------"
    # Connect A to Bi, create channels, create invoice from Bi, pay from A those invoices
    channel_info_A_Bi = []
    i = 1
    invoice_amt_a_bi = A_Bi_CHAN_VALUE / 2

    for bi_node in bi_nodes:
        print "## Connect A to B_" + str(i) + ":"
        print src_begin
        lnd.lnd_nodes[0].connect_to_node(bi_node.identity_pubkey, bi_node.ip_add)
        print src_end

        print "## Open channel to B_" + str(i) + " from A with " + str(A_Bi_CHAN_VALUE) + " satoshis:"
        print src_begin
        A_Bi_channel_funtxid, A_Bi_channel_output_index = lnd.lnd_nodes[0].open_channel(bi_node.identity_pubkey, A_Bi_CHAN_VALUE)
        print "- A<->B_" + str(
            i) + " Channel funtxid: " + A_Bi_channel_funtxid + ", Channel output index: " + A_Bi_channel_output_index

        print src_end

        print "## Create an invoice at node B_" + str(i) + " for " + str(invoice_amt_a_bi) + " Sathoshis:"
        print src_begin
        pay_req = bi_node.add_invoice(invoice_amt_a_bi)
        print src_end
        blockchain.generate_blocks(1, True)

        print "## Send payment from node A and check balances:"
        print src_begin
        output = lnd.lnd_nodes[0].send_payment(pay_req)

        # Check if they were problems sending the payment
        retries = 0
        while retries < 5:
            if "unable to find a path to destination" in output:
                print '-- There was an error sending the payment, retry sending again:'
                # The errror might come from not enough blocks to activate the channel
                blockchain.generate_blocks(6, True)
                time.sleep(5)
                if bi_node.is_channel_active(A_Bi_channel_funtxid, A_Bi_channel_output_index):
                    # Retry payment
                    print src_begin
                    output = lnd.lnd_nodes[0].send_payment(pay_req)
                    print src_end
            else:
                break
            retries = retries + 1
        print src_end

        print src_begin
        lnd.lnd_nodes[0].channel_balance(A_Bi_channel_funtxid)
        print src_end

        print "##  Check channel balance info on B_" + str(i)
        print src_begin
        bi_node.channel_balance(A_Bi_channel_funtxid)
        print src_end
        # Append Channel info to dict, it will be useful to close the channel later
        channel_info_A_Bi.append({"funtxid": A_Bi_channel_funtxid, "output_index": A_Bi_channel_output_index})
        i = i + 1

    print "## Check peers in A:"
    print src_begin
    lnd.lnd_nodes[0].list_peers()
    print src_end

    print "## Check if all channels between A<->B_i were opened:"
    print src_begin
    lnd.lnd_nodes[0].list_channels()
    print src_end

    # Loop through the Bi nodes so we will create 3 cases of cyclic routes:
    # - A <-> B_1 (LND) (with a number of hops of MAX_HOPS)
    # - A <-> B_2 (C-Lightning) (with a number of hops of MAX_HOPS)
    # - A <-> B_3 (Eclair) (with a number of hops of MAX_HOPS)
    j = 0
    for bi_node in bi_nodes:

        # Create a payment from M that goes through a cyclic route back to itself
        print "## Create an invoice at node A for " + str(ROUTE_PAYMENT_AMOUNT) + " Sathoshis:"
        print src_begin
        pay_req = lnd.lnd_nodes[0].add_invoice(ROUTE_PAYMENT_AMOUNT)
        print src_end
        # Get decoded information from previous pay_req
        decoded_pay_req = lnd.lnd_nodes[0].decode_payment_request(pay_req, True)
        payment_hash = decoded_pay_req["payment_hash"]
        blockchain.generate_blocks(1, True)

        node_type = ""
        node_name = ""
        if bi_node.identity_pubkey in lnd_nodes_name:
            node_type = "LND"
            node_name = lnd_nodes_name[bi_node.identity_pubkey]["topo_name"]
        elif bi_node.identity_pubkey in clightning_nodes_name:
            node_type = "C-Lightning"
            node_name = clightning_nodes_name[bi_node.identity_pubkey]["topo_name"]
        elif bi_node.identity_pubkey in eclair_nodes_name:
            node_type = "Eclair"
            node_name = eclair_nodes_name[bi_node.identity_pubkey]["topo_name"]

        # Check if bitcoin block count is the same as the B_i blockHeight
        if not bi_node.is_block_height_ok(blockchain.get_blockchain_block_count()):
            print "The node is not synchronized with the bitcoin blockchain, exiting!"
            exit(1)

        print "## Create route with "+str(MAX_HOPS)+" hops from A to "+node_name+" ("+node_type+") and back to A"

        # Get the template for routes by query a route from A to B1
        great_route = lnd.lnd_nodes[0].query_routes(lnd.lnd_nodes[1].identity_pubkey, ROUTE_PAYMENT_AMOUNT,True)
        # Clean the hops, they will be added in the following loop
        great_route["routes"][0]["hops"] = []

        for nhop in range(MAX_HOPS/2):
            # Get route from A to Bi
            a_bi_hop = lnd.lnd_nodes[0].query_routes(bi_node.identity_pubkey, ROUTE_PAYMENT_AMOUNT, True)["routes"][0]["hops"][0]
            # Append a_bi hop to great_route
            great_route["routes"][0]["hops"].append(a_bi_hop)

            # Append returning hop from B_i to A to form a loop
            # We can just change the previous hop and change the pub_key to the one of node A
            hop_A = a_bi_hop.copy()
            hop_A["chan_id"] = a_bi_hop["chan_id"]
            hop_A["pub_key"] = lnd.lnd_nodes[0].identity_pubkey
            great_route["routes"][0]["hops"].append(hop_A)

        # We will use the new_hops list to save the hops with the real expiry times, fees and amounts to forward
        new_hops = []
        num_hops = len(great_route["routes"][0]["hops"]) - 1

        # Make sure fees for last node hop are 0
        great_route["routes"][0]["hops"][num_hops]["fee"] = "0"
        great_route["routes"][0]["hops"][num_hops]["fee_msat"] = "0"
        # Initial expiry is the sum of a default expiry value + the number of blocks in the blockchain
        great_route["routes"][0]["hops"][num_hops]["expiry"] = DEFAULT_EXPIRY_DELTA + blockchain.get_blockchain_block_count()


        # Get the initial expiry to do further calculations, it will be the same as the expiry of the last node of the route
        hop_expiry = DEFAULT_EXPIRY_DELTA + blockchain.get_blockchain_block_count()
        # Get the amount to be forwarded to the final node
        prev_amt_to_forward_msat = int(great_route["routes"][0]["hops"][num_hops]["amt_to_forward_msat"])
        expiry_delta = 0
        prev_fee_msat = 0
        total_fees_msat = 0

        # Insert last hop to the list of modified hops
        new_hops.insert(0, great_route["routes"][0]["hops"][num_hops])

        # Start checking hops in a decreasing order from 1 node before the last one
        for i in range(num_hops - 1, -1, -1):
            hop = great_route["routes"][0]["hops"][i]

            # Expiry for current hop will take into account the values of previous hops
            hop_expiry = hop_expiry + expiry_delta

            # Update expiry value of current hop
            hop["expiry"] = hop_expiry

            # Get amounts to forward and fees
            amt_to_forward_msat = prev_amt_to_forward_msat + prev_fee_msat
            hop["amt_to_forward"] = str(int(amt_to_forward_msat / 1000))
            hop["amt_to_forward_msat"] = str(amt_to_forward_msat)

            # Get expiry, fee_base_msat and fee_rate_milli_msat from channel info and hops node_id
            expiry_delta, fee_base_msat, fee_rate_milli_msat = lnd.lnd_nodes[0].get_expiry_and_fees_from_channel(
                hop["chan_id"],
                hop["pub_key"],
                True)

            # Get fee_msat
            fee_msat = get_hop_fee_msat(fee_base_msat, amt_to_forward_msat, fee_rate_milli_msat)
            hop["fee_msat"] = str(fee_msat)
            hop["fee"] = str(int(fee_msat / 1000))
            new_hops.insert(0, hop)

            # Set values to be used by the next hop
            prev_amt_to_forward_msat = amt_to_forward_msat
            prev_fee_msat = fee_msat
            total_fees_msat = total_fees_msat + fee_msat

        # Final Timelock and fees
        great_route["routes"][0]["total_time_lock"] = hop_expiry + expiry_delta
        great_route["routes"][0]["total_fees"] = str(int(total_fees_msat / 1000))
        great_route["routes"][0]["total_fees_msat"] = str(total_fees_msat)
        total_amt_msat = ROUTE_PAYMENT_AMOUNT * 1000 + total_fees_msat
        great_route["routes"][0]["total_amt"] = str(int(total_amt_msat / 1000))
        great_route["routes"][0]["total_amt_msat"] = str(total_amt_msat)
        great_route["routes"][0]["hops"] = new_hops

        print "## Cyclic route to send the payment:"
        print src_begin
        print json.dumps(great_route, indent=4, sort_keys=True)
        print src_end

        print "## Check channel balance A <-> "+node_name+" before sending payment:"
        print src_begin
        lnd.lnd_nodes[0].channel_balance(channel_info_A_Bi[j]["funtxid"])
        print src_end

        print "## Send payment over the cyclic route:"
        print src_begin
        lnd.lnd_nodes[0].send_to_route(payment_hash, great_route)
        print src_end

        blockchain.generate_blocks(6, True)

        print "## Check channel balance A <-> "+node_name+" after payment on cyclic route:"
        print src_begin
        lnd.lnd_nodes[0].channel_balance(channel_info_A_Bi[j]["funtxid"])
        print src_end

        j = j + 1


if __name__ == '__main__':
    init_test()