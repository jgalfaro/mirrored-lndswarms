#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'ender'


class containerNode:
    def __init__(self):
        self.status = ""
        self.container_name = ""
        self.container_id = 0
        self.container_pid = 0
        self.container_ip_address = []
        self.init_command = ""
        self.init_env = ""

    def set_status(self, status):
        """
        Sets the status of the container
        :param status: the status of the container
        """
        if type(status) not in (basestring, unicode):
            raise TypeError("Expected value was string, value given is: ", type(status))
        self.status = status

    def set_pid(self, pid):
        """
        Sets the PID of the container
        :param pid: the PID of the container
        """
        if type(pid) is not int:
            raise TypeError("Expected value was integer, value given is: ", type(pid))
        self.container_pid = pid

    def set_container_ip_address(self, container_ip):
        """
        Sets the IP addresses of the container running
        :param container_ip: list of IP addresses of the container
        """
        if type(container_ip) not in (basestring, unicode):
            raise TypeError("Expected value was string, value given is: ", type(container_ip))
        self.container_ip_address = container_ip

    def set_init_command(self, init_command):
        """
        Sets the initial command that was used as entrypoint in the container
        :param init_command: the initial command that was used as entrypoint in the container
        """
        if type(init_command) not in (basestring, unicode):
            raise TypeError("Expected value was string, value given is: ", type(init_command))
        self.init_command = init_command

    def set_init_env(self, init_env):
        """
        Sets the initial environment variables that were used as to configure the container
        :param init_env: a list of strings with the initial environment variables that were used as to configure the container
        """
        if type(init_env) is not list:
            raise TypeError("Expected value was List, value given is: ", type(init_env))
        self.init_env = init_env

    def set_container_id(self, container_id):
        """
        Sets the ID of the container
        :param container_id: the ID of the container
        """
        if type(container_id) not in (basestring, unicode):
            raise TypeError("Expected value was string, value given is: ", type(container_id))
        self.container_id = container_id

    def set_container_name(self, container_name):
        """
        Sets the name of the container
        :param container_name: the name of the container
        """
        if type(container_name) not in (basestring, unicode):
            raise TypeError("Expected value was string, value given is: ", type(container_name))
        self.container_name = container_name

    def get_container_name(self):
        """
        Gets the name of the container
        :return string with the name of the container
        """
        return self.container_name

    def get_container_id(self):
        """
        Gets the ID of the container
        :return string with the ID of the container
        """
        return self.container_id

    def get_init_command(self):
        """
        init_command the initial environment variables that were used as to configure the container
        :returns a string containing the environment variables
        """
        return self.init_command

    def get_init_env(self):
        """
        init_command variable contains the command used as entrypoint in the container
        :returns a list of string containing the environment variables used to configure the container
        """
        return self.init_env

    def get_status(self):
        """
        Gets the status of the container running
        :return string with the status of the container
        """
        return self.status

    def get_pid(self):
        """
        Gets the PID of the container running
        :return string with the PID of the container
        """
        return self.container_pid

    def get_container_ip_address(self):
        """
        Gets the IP addresses of the container
        :return list with the IP address of the container
        """
        return self.container_ip_address
