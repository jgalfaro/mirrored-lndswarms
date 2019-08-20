#!/bin/bash

# exit from script if error was raised.
set -e

if [[ "$1" == "bitcoind" ||  "$1" == "bitcoin-cli" ||  "$1" == "bitcoin-tx" ||  "$1" == "test_bitcoin" ]];then
   echo $BITCOIN_EXTRA_ARGS > /root/.bitcoin/bitcoin.conf
   sed -i -e s/' '/'\n'/g /root/.bitcoin/bitcoin.conf
   echo "The following is the content of /root/.bitcoin/bitcoin.conf: "
   cat /root/.bitcoin/bitcoin.conf
   exec "$@"
fi
exec "$@"
