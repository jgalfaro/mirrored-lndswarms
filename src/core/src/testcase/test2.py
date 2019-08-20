#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
import time

from random import randint

from src.controller.bitcoindController import *
from src.controller.lnd_btcController import *
from src.controller.clightning_btcController import *
from src.controller.eclair_btcController import *
from src.utils.conf import *

def init_test():
    print '----- Starting Test 2 -----'

    lnd_nodes_name = {0:{'id': "M"}, 1:{'id': "A"},2:{'id': "B_1"}, 3:{'id': "B_2"}, 4:{'id': "B_3"}}
    clightning_nodes_name = {0:{'id': "B_4"}, 1:{'id': "B_5"}, 2:{'id': "B_6"}}
    eclair_nodes_name = {0:{'id': "B_7"}, 1:{'id': "B_8"}, 2:{'id': "B_9"}}

    bitcoind = bitcoindController()
    blockchain = bitcoind.bitcoind_node
    lnd = lnd_btcController(len(lnd_nodes_name))
    clight = clightning_btcController(len(clightning_nodes_name))
    eclair = eclair_btcController(len(eclair_nodes_name))

    # Test variables
    BLOCKS_TO_GENERATE = 500
    MIN_BTC_FUNDS_TO_SEND = 10
    M_A_CHAN_VALUE = 16777200
    A_Bi_CHAN_VALUE = 930900
    MAX_CONFIRMATION_BLKS = 40
    MIN_INVOICE_AMOUNT=1000

    bi_nodes = []
    if len(lnd.lnd_nodes) < len(lnd_nodes_name):
        print "Not enough LND nodes needed "+str(len(lnd_nodes_name))+", only "+str(len(lnd.lnd_nodes))
        exit(1)
    if len(clight.clightning_nodes) < len(clightning_nodes_name):
        print "Not enough C-Lightning nodes needed "+str(len(clightning_nodes_name))+", only "+str(len(clight.clightning_nodes))
        exit(1)
    """
    if len(eclair.eclair_nodes) < len(eclair_nodes_name):
        print "Not enough Eclair nodes needed "+str(len(eclair_nodes_name))+", only "+str(len(eclair.eclair_nodes))
        exit(1)
    """
    if not blockchain:
        print "There is not a Bitcoin-core instance running!"
        exit(1)

    print "## LND nodes information "
    for i in range(len(lnd_nodes_name)):
        print "- Node " + lnd_nodes_name[i]['id'] + " IP address: " + lnd.lnd_nodes[i].ip_add
        print "- Node " + lnd_nodes_name[i]['id'] + " ID: " + lnd.lnd_nodes[i].identity_pubkey
        if i > 1:
            bi_nodes.append(lnd.lnd_nodes[i])

    print "## C-Lightning nodes information "
    for i in range(len(clightning_nodes_name)):
        print "- Node " + clightning_nodes_name[i]['id'] + " IP address: " + clight.clightning_nodes[i].ip_add
        print "- Node " + clightning_nodes_name[i]['id'] + " ID: " + clight.clightning_nodes[i].identity_pubkey
        bi_nodes.append(clight.clightning_nodes[i])


    print "## Eclair nodes information "
    for i in range(len(eclair_nodes_name)):
        print "- Node " + eclair_nodes_name[i]['id'] + " IP address: " + eclair.eclair_nodes[i].ip_add
        print "- Node " + eclair_nodes_name[i]['id'] + " ID: " + eclair.eclair_nodes[i].identity_pubkey
        bi_nodes.append(eclair.eclair_nodes[i])


    print "## "+str(BLOCKS_TO_GENERATE)+" Blocks generation on bitcoin-core (at least 432 to activate segwit?):"
    blockchain.generate_blocks(BLOCKS_TO_GENERATE)

    print '## Blockchain info and segwit activation verification:'
    print '```'
    blockchain.get_blockchain_info()
    print '```'
    print "## M node address generation:"
    print '```'
    cmd_out = lnd.lnd_nodes[0].new_address()
    print '```'
    M_addr = cmd_out["address"]
    print "M address is: "+ M_addr

    print "## Send funds to M ("+str(MIN_BTC_FUNDS_TO_SEND)+"):"
    print '```'
    blockchain.send_funds_to_address(M_addr,MIN_BTC_FUNDS_TO_SEND)
    print '```'

    print "## Generate 1 block so the funds can be confirmed to M:"
    print '```'
    blockchain.generate_blocks(1)
    print '```'

    print "## Get M wallet balance:"
    print '```'
    lnd.lnd_nodes[0].wallet_balance()
    print '```'

    print "## A should generate an address an receive some funds to be able to open the channels::"
    print '```'
    cmd_out = lnd.lnd_nodes[1].new_address()
    print '```'
    A_addr = cmd_out["address"]
    print "A address is: "+ A_addr

    print "## Send funds to A ("+str(MIN_BTC_FUNDS_TO_SEND)+"):"
    print '```'
    blockchain.send_funds_to_address(A_addr, MIN_BTC_FUNDS_TO_SEND)
    print '```'

    print "## Generate 1 block so the funds can be confirmed to A:"
    print '```'
    blockchain.generate_blocks(1)
    print '```'

    print "## Get A wallet balance:"
    print '```'
    lnd.lnd_nodes[1].wallet_balance()
    print '```'

    print "## Connect M to A:"
    print '```'
    lnd.lnd_nodes[0].connect_to_node(lnd.lnd_nodes[1].identity_pubkey, lnd.lnd_nodes[1].ip_add)
    print '```'

    print "## Check peers in M:"
    print '```'
    lnd.lnd_nodes[0].list_peers()
    print '```'

    print "## Open channel to A from M with "+str(M_A_CHAN_VALUE)+" satoshis:"
    print '```'
    M_A_channel_funtxid, M_A_channel_output_index = lnd.lnd_nodes[0].open_channel(lnd.lnd_nodes[1].identity_pubkey, M_A_CHAN_VALUE)
    print "- M<->A Channel funtxid: " + M_A_channel_funtxid + ", Channel output index: " + M_A_channel_output_index


    print "## Check if channel was opened:"
    print '```'
    lnd.lnd_nodes[0].list_channels()
    print '```'

    channel_info_A_Bi = []
    i = 1

    for bi_node in bi_nodes:
        print "## Connect A to B_"+str(i)+":"
        print '```'

        lnd.lnd_nodes[1].connect_to_node(bi_node.identity_pubkey, bi_node.ip_add)
        print '```'

        print "## Open channel to B_"+str(i)+" from A with " + str(A_Bi_CHAN_VALUE) + " satoshis:"
        print '```'
        A_Bi_channel_funtxid, A_Bi_channel_output_index = lnd.lnd_nodes[1].open_channel(bi_node.identity_pubkey, A_Bi_CHAN_VALUE)
        print "- A<->B_"+str(i)+" Channel funtxid: " + A_Bi_channel_funtxid + ", Channel output index: " + A_Bi_channel_output_index
        # Append Channel info to dict, it will be useful to close the channel later
        channel_info_A_Bi.append({"funtxid": A_Bi_channel_funtxid, "output_index": A_Bi_channel_output_index})
        i = i + 1


    print "## Check peers in A:"
    print '```'
    lnd.lnd_nodes[1].list_peers()
    print '```'

    print "## Check if all channels between A<->B_i were opened:"
    print '```'
    lnd.lnd_nodes[1].list_channels()
    print '```'

    i = 1
    for bi_node in bi_nodes:

        invoice_amt = randint(1, 9) * MIN_INVOICE_AMOUNT
        print "## Create an invoice at node B_"+str(i)+" for "+str(invoice_amt)+" Sathoshis:"
        print '```'
        pay_req = bi_node.add_invoice(invoice_amt)
        print '```'
        blockchain.generate_blocks(1, True)

        print "## Send payment from node M and check balance:"
        print '```'
        output = lnd.lnd_nodes[0].send_payment(pay_req)
        print '```'

        # Check if they were problems sending the payment
        retries = 0
        while retries < 5:
            if "unable to find a path to destination" in output:
                print '-- There was an error sending the payment, retry sending again:'
                # The errror might come from not enough blocks to activate the channel
                blockchain.generate_blocks(6, True)
                time.sleep(5)
                if bi_node.is_channel_active(channel_info_A_Bi[i-1]['funtxid'], channel_info_A_Bi[i-1]['output_index']):
                    # Retry payment
                    print '```'
                    output = lnd.lnd_nodes[0].send_payment(pay_req)
                    print '```'
            else:
                break
            retries = retries + 1

        print '```'
        lnd.lnd_nodes[0].channel_balance(channel_info_A_Bi[i-1]['funtxid'])
        print '```'

        print "##  Check channel balance info on B_"+str(i)
        print '```'
        bi_node.channel_balance(channel_info_A_Bi[i-1]['funtxid'])
        print '```'

        print "## Close channel on A and check walletbalance:"
        print '```'
        lnd.lnd_nodes[1].close_channel(channel_info_A_Bi[i-1]['funtxid'], channel_info_A_Bi[i-1]['output_index'])
        lnd.lnd_nodes[1].wallet_balance()
        print '```'

        print "## Generate 1 block to include the close transaction into the blockchain, check M and B_"+str(i)+" wallet balances:"
        print '```'
        blockchain.generate_blocks(1)
        lnd.lnd_nodes[0].wallet_balance()
        bi_node.wallet_balance()
        i = i+1
        print '```'

if __name__ == '__main__':
    init_test()