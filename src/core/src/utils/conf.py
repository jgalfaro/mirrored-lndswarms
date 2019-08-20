DOCKER_STACK_PREFIX = 'testbed'

# Network settings
NETWORK_NAME = DOCKER_STACK_PREFIX+"_lnd_network"
NETWORK_SUBNET = '10.10.10.0/24'
NETWORK_GATEWAY = '10.10.10.1'

# RPC settings
RPC_USER = 'rpcuser'
RPC_PASS = 'rpcpass'
BITCOIN_NETWORK = 'regtest'

# Blockchain Node container variables
BLOCKCHAIN_IMG_NAME = 'enderalvarez/lightning-test:bitcoind'
BLOCKCHAIN_HOSTNAME = 'blockchain'
BLOCKCHAIN_CONTAINER_NAME = DOCKER_STACK_PREFIX+'_bitcoind'
BLOCKCHAIN_CONTAINER_ENV = {"BITCOIN_EXTRA_ARGS": BITCOIN_NETWORK+"=1\
    server=1\
    rpcuser="+RPC_USER+"\
    rpcpassword="+RPC_PASS+"\
    rpcallowip=0.0.0.0/0\
    txindex=1\
    addresstype=p2sh-segwit\
    whitelist=0.0.0.0/0\
    deprecatedrpc=signrawtransaction\
    zmqpubrawtxhwm=10000\
    zmqpubrawblock=tcp://0.0.0.0:28332\
    zmqpubrawtx=tcp://0.0.0.0:28332"
    }
BLOCKCHAIN_COMMAND_PREFIX = 'bitcoin-cli -'+BITCOIN_NETWORK+' '
BLOCKCHAIN_VOLUME_NAME = DOCKER_STACK_PREFIX+"_bitcoin_volume"
BLOCKCHAIN_VOLUME_MOUNT_POINT = "/root/.bitcoin/"


# Lightning Node container variables
LND_NODE_IMG_NAME = 'enderalvarez/lightning-test:lnd_bitcoind'
LND_SERVICE_NAME = 'lnd_btc'
LND_COMMAND_PREFIX = 'lncli -network='+BITCOIN_NETWORK+' '
LND_CONTAINER_ENV = {"BITCOIN_EXTRA_ARGS": BITCOIN_NETWORK+"=1\
    server=1\
    rpcuser="+RPC_USER+"\
    rpcpassword="+RPC_PASS+"\
    txindex=1\
    addresstype=p2sh-segwit\
    deprecatedrpc=signrawtransaction\
    zmqpubrawtxhwm=10000\
    regtest.addnode="+BLOCKCHAIN_CONTAINER_NAME+":18444",
    "RPCUSER": RPC_USER,
    "RPCPASS": RPC_PASS,
    "NETWORK": BITCOIN_NETWORK}


# C-lightning Node container variables
CLIGHTNING_NODE_IMG_NAME = 'elementsproject/lightningd'
CLIGHTNING_SERVICE_NAME = 'clightning_btc'
CLIGHTNING_COMMAND_PREFIX = 'lightning-cli '
CLIGHTNING_CONTAINER_ENV = {"EXPOSE_TCP": "true"}
CLIGHTNING_CONTAINER_COMMAND = ["--bitcoin-rpcconnect="+BLOCKCHAIN_CONTAINER_NAME,
                                "--bitcoin-rpcuser="+RPC_USER,
                                "--bitcoin-rpcpassword="+RPC_PASS,
                                "--ignore-fee-limits=true",
                                "--network="+BITCOIN_NETWORK,
                                "--plugin-dir=/usr/libexec/c-lightning/plugins/",
                                "--log-level=debug"]
# Eclair Node container variables
ECLAIR_NODE_IMG_NAME = 'enderalvarez/lightning-test:eclaird'
ECLAIR_SERVICE_NAME = 'eclair_btc'
ECLAIR_API_PASSWORD = 'eclairapi'
ECLAIR_COMMAND_PREFIX = 'eclair-cli -p '+ECLAIR_API_PASSWORD+' '
ECLAIR_CONTAINER_ENV = {"JAVA_OPTS": "\
          -Xms512m\
          -Declair.api.enabled=true\
          -Declair.api.password="+ECLAIR_API_PASSWORD+"\
          -Declair.chain=regtest\
          -Declair.bitcoind.host="+BLOCKCHAIN_CONTAINER_NAME+"\
          -Declair.bitcoind.rpcport=18443\
          -Declair.bitcoind.rpcuser="+RPC_USER+"\
          -Declair.bitcoind.rpcpassword="+RPC_PASS+"\
          -Declair.bitcoind.zmqblock=tcp://"+BLOCKCHAIN_CONTAINER_NAME+":28332\
          -Declair.bitcoind.zmqtx=tcp://"+BLOCKCHAIN_CONTAINER_NAME+":28332\
          -Declair.headless\
          -Declair.printToConsole"
          }
ECLAIR_CONTAINER_COMMAND = ""
