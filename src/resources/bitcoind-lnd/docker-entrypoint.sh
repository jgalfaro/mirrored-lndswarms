#!/bin/bash


# error function is used within a bash function in order to send the error
# message directly to the stderr output and exit.
error() {
    echo "$1" > /dev/stderr
    exit 0
}

# return is used within bash function in order to return the value.
return() {
    echo "$1"
}

# set_default function gives the ability to move the setting of default
# env variable from docker file to the script thereby giving the ability to the
# user override it durin container start.
set_default() {
    # docker initialized env variables with blank string and we can't just
    # use -z flag as usually.
    BLANK_STRING='""'

    VARIABLE="$1"
    DEFAULT="$2"

    if [[ -z "$VARIABLE" || "$VARIABLE" == "$BLANK_STRING" ]]; then

        if [ -z "$DEFAULT" ]; then
            error "You should specify default variable"
        else
            VARIABLE="$DEFAULT"
        fi
    fi

   return "$VARIABLE"
}


# bitcoind configuration
echo $BITCOIN_EXTRA_ARGS > /root/.bitcoin/bitcoin.conf
sed -i -e s/' '/'\n'/g /root/.bitcoin/bitcoin.conf
echo "zmqpubrawblock=tcp://127.0.0.1:28332" >> /root/.bitcoin/bitcoin.conf
echo "zmqpubrawtx=tcp://127.0.0.1:28333"  >> /root/.bitcoin/bitcoin.conf
echo "The following is the content of /root/.bitcoin/bitcoin.conf: "
cat /root/.bitcoin/bitcoin.conf
bitcoind -daemon

# Wait for daemon to start
re="^[0-9]+$"
retries=0
while [ $retries -lt 5 ]
do
        uptime=$(bitcoin-cli uptime 2>/dev/null)
        if [[ $uptime =~ $re ]]
	then
		if  [ $uptime -gt 0 ]  
		then 
			echo 'bitcoind is running!' 
			break 
	
		fi
	fi
	echo 'bitcoind not running!'
	retries=$((retries+1))
	sleep 3
done
# LND configuration
RPCHOST=$(set_default "$RPCHOST" "127.0.0.1")
RPCUSER=$(set_default "$RPCUSER" "rpcuser")
RPCPASS=$(set_default "$RPCPASS" "rpcpass")
DEBUG=$(set_default "$DEBUG" "debug")
NETWORK=$(set_default "$NETWORK" "regtest")
CHAIN=$(set_default "$CHAIN" "bitcoin")
BACKEND=$(set_default "$BACKEND" "bitcoind")

exec lnd \
    --noseedbackup \
    --logdir="/data" \
    "--$CHAIN.active" \
    "--$CHAIN.$NETWORK" \
    "--$CHAIN.node"="$BACKEND" \
    "--$BACKEND.rpchost"="$RPCHOST" \
    "--$BACKEND.rpcuser"="$RPCUSER" \
    "--$BACKEND.rpcpass"="$RPCPASS" \
    "--$BACKEND.zmqpubrawblock=tcp://$RPCHOST:28332" \
    "--$BACKEND.zmqpubrawtx=tcp://$RPCHOST:28333" \
    --debuglevel="debug" \
    "$@"
