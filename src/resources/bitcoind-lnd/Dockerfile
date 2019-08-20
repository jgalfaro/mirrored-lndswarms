# Initial image used to compile bitcoin-core and LND
FROM debian:stretch-slim as builder

# Force Go to use the cgo based DNS resolver. This is required to ensure DNS
# queries required to connect to linked containers succeed.
ENV GODEBUG netdns=cgo
ENV GOPATH=/go

# Install depedencies for both bitcoin-core and LND
RUN apt-get update  \
&& apt-get install -y \
  build-essential \
  git \
  libtool \ 
  autotools-dev \
  automake \
  pkg-config \
  bsdmainutils \
  python3 \
  libssl-dev \
  libevent-dev \
  libboost-system-dev \
  libboost-filesystem-dev \
  libboost-chrono-dev \
  libboost-test-dev \
  libboost-thread-dev \
  libzmq3-dev \
  wget \
&& rm -rf /var/lib/apt/lists/*

# --------------------------------------
# Bitcoin-core install and config
# --------------------------------------
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
RUN strip ${BITCOIN_INSTALL_DIR}/lib/libbitcoinconsensus.a
RUN strip ${BITCOIN_INSTALL_DIR}/lib/libbitcoinconsensus.so.0.0.0


# --------------------------------------
# LND install and config
# --------------------------------------
RUN wget https://dl.google.com/go/go1.11.5.linux-amd64.tar.gz \
&& tar -C /usr/local -xzf go1.11.5.linux-amd64.tar.gz \
&& export PATH=/usr/local/go/bin:$PATH \
&& go get -d github.com/lightningnetwork/lnd \
&& cd $GOPATH/src/github.com/lightningnetwork/lnd \
&& git pull \
&& make clean \
&& make \
&& make install

RUN strip $GOPATH/bin/*

# --------------------------------------
# Creation of final image
# -------------------------------------
FROM debian:stretch-slim
MAINTAINER ender.alvarez@it-sudparis.eu

ENV BITCOIN_VERSION=0.17.1
ENV BITCOIN_INSTALL_DIR=/usr/bin/bitcoin-${BITCOIN_VERSION}

# Copy the result of the bitcoin installation in builder image
COPY --from=builder $BITCOIN_INSTALL_DIR $BITCOIN_INSTALL_DIR
ENV PATH=${BITCOIN_INSTALL_DIR}/bin:$PATH

# Copy the LND binaries from the builder image.
COPY --from=builder /go/bin/lncli /bin/
COPY --from=builder /go/bin/lnd /bin/

# Install bitcoin dependencies into the debian system
RUN apt-get update && \
apt-get install -y openssl libzmq5 libevent-2.0-5 libevent-pthreads-2.0-5 libboost-system1.62.0 libboost-filesystem1.62.0 libboost-chrono1.62.0 libboost-thread1.62.0 --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Create bitcoin data dir folder
RUN mkdir -p /root/.bitcoin/

# Copy the entrypoint to image
COPY docker-entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Expose lnd ports (server, rpc).
EXPOSE 9735 10009

# Expose mainnet ports (server, rpc)
EXPOSE 8332 8333 8334

# Expose testnet ports (server, rpc)
EXPOSE 18332 18333 18334

# Expose regtest ports (server, rpc)
EXPOSE 18443 18444
