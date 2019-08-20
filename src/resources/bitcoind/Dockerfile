# Initial image used to compile bitcoin-core
FROM debian:stretch-slim as bitcoin-core

# Install depedencies
RUN apt-get update && apt-get install -y build-essential libtool autotools-dev automake pkg-config bsdmainutils python3 libssl-dev libevent-dev libboost-system-dev libboost-filesystem-dev libboost-chrono-dev libboost-test-dev libboost-thread-dev libzmq3-dev wget && rm -rf /var/lib/apt/lists/*

# Download bitcoin source code 
ENV BITCOIN_VERSION=0.17.1
RUN mkdir /usr/src/bitcoin 
WORKDIR /usr/src/bitcoin
RUN wget https://bitcoin.org/bin/bitcoin-core-${BITCOIN_VERSION}/bitcoin-${BITCOIN_VERSION}.tar.gz
RUN tar -xzf *.tar.gz
WORKDIR /usr/src/bitcoin/bitcoin-${BITCOIN_VERSION}

# Install Berkeley DB using the script provide by the bitcoin-core developers
# then configure and install bitcoin-core from source
ENV BITCOIN_INSTALL_DIR=/usr/bin/bitcoin-${BITCOIN_VERSION}
RUN ./contrib/install_db4.sh `pwd`
RUN  export BDB_PREFIX=/usr/src/bitcoin/bitcoin-$BITCOIN_VERSION/db4 && ./autogen.sh && \
    ./configure --prefix=${BITCOIN_INSTALL_DIR} BDB_LIBS="-L${BDB_PREFIX}/lib -ldb_cxx-4.8" BDB_CFLAGS="-I${BDB_PREFIX}/include"
RUN make -j3
RUN make install

# Strip the binaries and libraries to reduce their size
RUN strip ${BITCOIN_INSTALL_DIR}/bin/*
#RUN strip ${BITCOIN_INSTALL_DIR}/lib/*
#RUN strip ${BITCOIN_INSTALL_DIR}/bin/bitcoin-cli
#RUN strip ${BITCOIN_INSTALL_DIR}/bin/bitcoin-tx
#RUN strip ${BITCOIN_INSTALL_DIR}/bin/bitcoind
#RUN strip ${BITCOIN_INSTALL_DIR}/bin/test_bitcoin
RUN strip ${BITCOIN_INSTALL_DIR}/lib/libbitcoinconsensus.a
RUN strip ${BITCOIN_INSTALL_DIR}/lib/libbitcoinconsensus.so.0.0.0


# Final image to be used
FROM debian:stretch-slim
MAINTAINER ender.alvarez@it-sudparis.eu

ENV BITCOIN_VERSION=0.17.1
ENV BITCOIN_INSTALL_DIR=/usr/bin/bitcoin-${BITCOIN_VERSION}

# Copy the result of the bitcoin installation in bitcoin-core image
COPY --from=bitcoin-core $BITCOIN_INSTALL_DIR $BITCOIN_INSTALL_DIR
ENV PATH=${BITCOIN_INSTALL_DIR}/bin:$PATH

# Install bitcoin dependencies into the debian system
RUN apt-get update && \
apt-get install -y openssl libzmq5 libevent-2.0-5 libevent-pthreads-2.0-5 libboost-system1.62.0 libboost-filesystem1.62.0 libboost-chrono1.62.0 libboost-thread1.62.0 --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Create data dir folder
RUN mkdir -p /root/.bitcoin/

# Bitcoin datadir volume
VOLUME ["/root/.bitcoin/"]

# Copy the entrypoint to image
COPY docker-entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Expose mainnet ports (server, rpc)
EXPOSE 8332 8333 8334

# Expose testnet ports (server, rpc)
EXPOSE 18332 18333 18334

# Expose regtest ports (server, rpc)
EXPOSE 18443 18444 

# Expose zmq ports
ARG zmqpubrawblockport
ARG zmqpubrawtx
EXPOSE $zmqpubrawblockport $zmqpubrawtx

# Default command to be run
CMD ["bitcoind"]







