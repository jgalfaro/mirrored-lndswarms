#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
from random import randint

from src.controller.bitcoindController import *
from src.controller.lnd_btcController import *
from src.utils.conf import *


def init_test():
    print '----- Starting Test 1 -----'
    lnd_nodes_names = {0: {'id': "M"}, 1: {'id': "A"}}

    bitcoind = bitcoindController()
    blockchain = bitcoind.bitcoind_node
    lnd = lnd_btcController(len(lnd_nodes_names))

    # Test variables
    BLOCKS_TO_GENERATE = 500
    MIN_BTC_FUNDS_TO_SEND = 10
    CHAN_VALUE = 16777200
    MAX_CONFIRMATION_BLKS = 30
    MIN_INVOICE_AMOUNT=10000

    if len(lnd.lnd_nodes) < len(lnd_nodes_names):
        print "Not enough LND nodes needed " + str(len(lnd_nodes_names)) + ", only " + str(len(lnd.lnd_nodes))
        exit(1)
    if not blockchain:
        print "There is not a Bitcoin-core instance running!"
        exit(1)

    print "## LND nodes information "
    for i in range(len(lnd_nodes_names)):
        print "- Node " + lnd_nodes_names[i]['id'] + " IP address: " + lnd.lnd_nodes[i].ip_add
        print "- Node " + lnd_nodes_names[i]['id'] + " ID: " + lnd.lnd_nodes[i].identity_pubkey

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
    blockchain.send_funds_to_address(M_addr, MIN_BTC_FUNDS_TO_SEND)
    print '```'

    print "## Generate 1 block so the funds can be confirmed to M:"
    print '```'
    blockchain.generate_blocks(1)
    print '```'

    print "## Get M wallet balance:"
    print '```'
    lnd.lnd_nodes[0].wallet_balance()
    print '```'

    print "## Connect M to A:"
    print '```'
    lnd.lnd_nodes[0].connect_to_node(lnd.lnd_nodes[1].identity_pubkey, lnd.lnd_nodes[1].ip_add)
    print '```'

    print "## Check peers in M:"
    print '```'
    lnd.lnd_nodes[0].list_peers()
    print '```'

    print "## Open chanel to A from M with "+str(CHAN_VALUE)+" satoshis:"
    print '```'
    M_A_channel_funtxid, M_A_channel_output_index = lnd.lnd_nodes[0].open_channel(lnd.lnd_nodes[1].identity_pubkey, CHAN_VALUE)
    print "M<->A Channel funtxid: " + M_A_channel_funtxid + ", Channel output index: " + M_A_channel_output_index
    print '```'

    print "## Check if channel was opened:"
    print '```'
    lnd.lnd_nodes[0].list_channels()
    print '```'

    print "## - Check wallet balance on M:"
    print '```'
    lnd.lnd_nodes[0].wallet_balance()
    print '```'

    invoice_amt = randint(1, 9) * MIN_INVOICE_AMOUNT
    print "## Create an invoice at node A for "+str(invoice_amt)+" Sathoshis and check channel balance:"
    print '```'
    pay_req = lnd.lnd_nodes[1].add_invoice(invoice_amt)
    lnd.lnd_nodes[1].channel_balance(M_A_channel_funtxid)
    print '```'

    print "## Check wallet balance on M:"
    print '```'
    lnd.lnd_nodes[0].wallet_balance()
    print '```'

    print "## Check balance on channel from node M and send payment from node M:"
    print '```'
    lnd.lnd_nodes[0].channel_balance(M_A_channel_funtxid)
    lnd.lnd_nodes[0].send_payment(pay_req)
    print '```'

    print "##  Check channel balance and channel info on A:"
    print '```'
    lnd.lnd_nodes[1].channel_balance(M_A_channel_funtxid)
    lnd.lnd_nodes[1].list_channels()
    print '```'

    invoice_amt = randint(1, 9) * MIN_INVOICE_AMOUNT
    print "## Create another invoice at node A for "+str(invoice_amt)+" Sathoshis:"
    print '```'
    pay_req = lnd.lnd_nodes[1].add_invoice(invoice_amt)
    print '```'

    print "## Send payment from node M and check balance:"
    print '```'
    lnd.lnd_nodes[0].send_payment(pay_req)
    lnd.lnd_nodes[0].channel_balance(M_A_channel_funtxid)
    print '```'

    print "##  Check channel balance and channel info on A:"
    print '```'
    lnd.lnd_nodes[1].channel_balance(M_A_channel_funtxid)
    lnd.lnd_nodes[1].list_channels()
    print '```'

    print "## Close channel on A and check walletbalance:"
    print '```'
    lnd.lnd_nodes[1].close_channel(M_A_channel_funtxid, M_A_channel_output_index)
    lnd.lnd_nodes[1].wallet_balance()
    print '```'

    print "## Check walletbalance on M:"
    print '```'
    lnd.lnd_nodes[0].wallet_balance()
    print '```'

    print "## Generate 1 block to include the close transaction into the blockchain, check M and A wallet balances:"
    print '```'
    blockchain.generate_blocks(1)
    lnd.lnd_nodes[0].wallet_balance()
    lnd.lnd_nodes[1].wallet_balance()
    print '```'


if __name__ == '__main__':
    init_test()