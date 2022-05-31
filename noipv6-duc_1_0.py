#!/usr/bin/env python3

from abc import ABC, abstractmethod
import configparser
import logging
import ipaddress
import requests
import subprocess
import socket
import os
from time import sleep

LOG = logging.getLogger("noipv6-duc")
logging.basicConfig(level=logging.DEBUG)

NO_IP_UPDATE_URL = "https://dynupdate.no-ip.com/nic/update"
CONFIG_PATH = "/usr/local/etc/noipv6-duc/config.ini"

class Config:
	def __init__(self, host_name, interval, user, password):
		self.host_name = host_name
		self.interval = int(interval)
		self.user = user
		self.password = password

def parser_config(file_name):
	if not os.path.isfile(file_name):
		raise ValueError("{} is not a file".format(file_name))

	parser = configparser.ConfigParser()
	parser.read(file_name)
	host_name = parser["host"]["host_name"]
	interval = parser["host"]["interval"]
	user = parser["auth"]["user"]
	password = parser["auth"]["password"]
	return Config(host_name, interval, user, password)

class NoIpReturnCode:

	def __init__(self, status, success, description):
		self.status = status
		self.success = success
		self.description = description

	def __str__(self):
		return "{} - {} - {}".format("SUCCESS" if self.success else "FAILURE", self.status, self.description)

def parse_no_ip_return_code(status):
	# see: https://www.noip.com/integrate/response
	if status.startswith("good "):
		return NoIpReturnCode(status, True, "DNS hostname update successful.")
	elif status.startswith("nochg "):
		return NoIpReturnCode(status, True, "IP address is current, no update performed.")
	elif status == "nohost":
		return NoIpReturnCode(status, False, "Hostname supplied does not exist under specified account.")
	elif status == "badauth":
		return NoIpReturnCode(status, False, "Invalid username password combination.")
	elif status == "badagent":
		return NoIpReturnCode(status, False, "Client disabled. Client should exit and not perform any more updates without user intervention.")
	elif status == "!donator":
		return NoIpReturnCode(status, False, "An update request was sent, including a feature that is not available to that particular user such as offline options.")
	elif status == "abuse":
		return NoIpReturnCode(status, False, "Username is blocked due to abuse. Either for not following our update specifications or disabled due to violation of the No-IP terms of service.")
	elif status == "911":
		return NoIpReturnCode(status, False, "A fatal error on our side such as a database outage. Retry the update no sooner than 30 minutes.")
	else:
		raise ValueError("Unknown statuts: {}".format(status))

def is_valid_ipv6_addr(addr):
	try:
		ipaddress.IPv6Network(addr)
		return True
	except ValueError:
		return False

def get_ipv6_addr():
	addrs = subprocess.check_output("hostname -I", shell=True).decode("utf-8").strip().split(" ")
	LOG.debug("addrs = %s", addrs)
	valid_addrs = [a for a in addrs if is_valid_ipv6_addr(a)]
	LOG.debug("valid_addrs = %s", valid_addrs)
	if len(valid_addrs) == 0:
		raise ValueError("This device does not have a IPv6 address")
	return valid_addrs[0]


def main():
	LOG.info("Parsing config: %s", CONFIG_PATH)

	config = parser_config(CONFIG_PATH)

	LOG.info("Host is: '%s'", config.host_name)
	LOG.info("Checking for new ip every %s minutes", config.interval)


	old_ipv6 = ""
	while True:
		my_ipv6 = get_ipv6_addr()
		LOG.info("Current ip is %s", my_ipv6)

		if my_ipv6 != old_ipv6:
			LOG.info("Detected a new ipv6 address, updating no ip")
			# 0.0.0.0 is prefixed to "disable" ipv4

			parameters = {'hostname': config.host_name, 'myip': "0.0.0.0," + my_ipv6}
			requestHeader = {'User-Agent': 'Personal noipv6-duc_1_0.py/linux-v5.0'}

			get_result = requests.get(url = NO_IP_UPDATE_URL, params = parameters, auth=(config.user, config.password))
			LOG.debug("get_result.text = %s", get_result.text.strip())

			return_code = parse_no_ip_return_code(get_result.text.strip())
			LOG.info("return_code = %s", return_code)

			# server side error, we might continue in 30 minutes
			if return_code.status == "911":
				sleep(30 * 60)
				continue

			# client side error -> abort
			if not return_code.success:
				raise ValueError("Got NOIP return code: {}". format(return_code))
			
			old_ipv6 = my_ipv6

		LOG.debug("Next check in %s minutes, sleeping now...", config.interval)
		sleep(config.interval * 60)


if __name__ == '__main__':
	main()
