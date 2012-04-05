#!/usr/bin/python

HISTORY=1000
DEBUG=False
PATH='var/run/ptalk.sock'
MOTD='motd'

if __name__ == "__main__":
	print open("config.py").read()
