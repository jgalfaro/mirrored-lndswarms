#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'
from dockerUtilities import *
from conf import *
import test1 as test1
import test2 as test2
#import test3 as test3
import argparse


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

    # Check if overlay network is already created, otherwise create it
    try:
        test_network = docker_utils.docker_client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        # Create Network
        print 'Creating overlay network: ' + NETWORK_NAME
        docker_utils.create_overlay_network()

    # Check if bitcoind volume has been created already, if so delete and recreate later
    try:
        docker_utils.docker_client.volumes.get(BLOCKCHAIN_VOLUME_NAME)
    except docker.errors.NotFound:
        # Create Volume
        print 'Creating volume: ' + BLOCKCHAIN_VOLUME_NAME
        docker_utils.docker_client.volumes.create(BLOCKCHAIN_VOLUME_NAME)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", help="Number of the test that you want to execute")
    parser.add_argument("--clean", help="Clean the docker testbed (remove containers, networks, volumes created)",
                        action="store_true")
    args = parser.parse_args()

    if args.clean:
        clean_docker_testbed()

    if args.test:
        args_values = parser.parse_args()
        test_number = int(args_values.test)
        if (test_number > 3) or (test_number <= 0):
            print "Wrong value for number of test: "+args_values.test
            exit(1)

        if test_number== 1:
            clean_docker_testbed()
            test1.init_test()
        elif test_number == 2:
            clean_docker_testbed()
            test2.init_test()
        elif test_number == 3:
            #clean_docker_testbed()
            #test3.init_test()
            print "Test 3 is under development!"

    else:
        print "Usage:"
        print "-h           Print help"
        print "--test       The test number you want to run"
        print "--clean      Remove all docker containers, volumes and networks created for the testbed"
