#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
import argparse
import docker

from utils.dockerUtilities import *
from utils.conf import *

from testcase import test1 as test1
from testcase import test2 as test2
from testcase import test3 as test3
from testcase import test4 as test4
from testcase import test5 as test5

def clean_docker_testbed():
    docker_utils = DockerUtilities()

    # Delete containers if they are already created
    try:
        running_containers = docker_utils.docker_client.containers.list(all=True,
                                                                        filters={"name": DOCKER_STACK_PREFIX})
        for cont in running_containers:
            print 'Removing container: ' + cont.id
            cont.remove(force=True)
    except docker.errors.APIError:
        print "Error deleting the containers with prefix: " + DOCKER_STACK_PREFIX

    # Check if overlay network is created if so remove it
    print "Check if network: "+ NETWORK_NAME +" is created"
    docker_utils.delete_overlay_network(NETWORK_NAME)

    # Check if bitcoind volume has been created already, if so delete it
    try:
        volume = docker_utils.docker_client.volumes.get(BLOCKCHAIN_VOLUME_NAME)
        volume.remove(force=True)
        print 'Volume ' + BLOCKCHAIN_VOLUME_NAME + ' is deleted'
    except docker.errors.NotFound:
        print 'Volume ' + BLOCKCHAIN_VOLUME_NAME + ' not found'

def create_network_and_volume():
    docker_utils = DockerUtilities()
    # Check if overlay network is already created, otherwise create it
    try:
        print "Check if network: "+ NETWORK_NAME +" is created"
        network = docker_utils.docker_client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        # Create Network
        print 'Creating overlay network: ' + NETWORK_NAME
        docker_utils.create_overlay_network()

    # Check if bitcoind volume has been created already, if so delete and recreate later
    try:
        volume = docker_utils.docker_client.volumes.get(BLOCKCHAIN_VOLUME_NAME)
        volume.remove(force=True)
    except docker.errors.NotFound:
        # Create Volume
        print 'Creating volume: ' + BLOCKCHAIN_VOLUME_NAME
    docker_utils.docker_client.volumes.create(BLOCKCHAIN_VOLUME_NAME)


if __name__ == '__main__':
    fees_zero = False
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", help="Number of the test that you want to execute")
    parser.add_argument("--clean", help="Clean the docker testbed (remove containers, networks, volumes created)",
                        action="store_true")
    args = parser.parse_args()

    if args.clean:
        clean_docker_testbed()
        exit(0)

    if args.test:
        args_values = parser.parse_args()
        test_number = int(args_values.test)
        if (test_number > 5) or (test_number <= 0):
            print "Wrong value for number of test: "+args_values.test
            exit(1)
        clean_docker_testbed()
        create_network_and_volume()

        if test_number== 1:
            test1.init_test()
        elif test_number == 2:
            test2.init_test()
        elif test_number == 3:
            test3.init_test()
        elif test_number == 4:
            test4.init_test()
        elif test_number == 5:
            test5.init_test()

    else:
        print "Usage:"
        print "-h           Print help"
        print "--test       The test number you want to run"
        print "--clean      Remove all docker containers, volumes and networks created for the testbed"
        exit(0)
