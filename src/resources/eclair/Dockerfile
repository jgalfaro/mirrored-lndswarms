# Use the original eclair image
FROM acinq/eclair

# Then install the needed dependencies to run eclair-cli as well
RUN apt-get update && apt-get install jq curl -y && rm -rf /var/lib/apt/lists/*

COPY eclair-cli /bin/eclair-cli
RUN chmod +x /bin/eclair-cli

VOLUME ["/data"]

ENTRYPOINT java $JAVA_OPTS -Declair.datadir=$ECLAIR_DATADIR -jar eclair-node.jar






