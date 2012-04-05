#!/usr/bin/python

import os, socket, select
import config

def ts():
        import time
        return time.strftime("%H:%M:%S", time.gmtime())

class Client:
	def __init__(self, parent, client):
		self.parent = parent
		self.client = client
		self.ulogin = None
		self.buffer = ""

	def close(self):
		self.client.close()

	def send(self, message):
		self.client.send(message)

	def recv(self):
		self.buffer += self.client.recv(1024)
		messages = self.buffer.splitlines()
		if self.buffer.endswith("\n"):
			self.buffer = ""
		else:
			self.buffer = messages.pop()
		for message in messages:
			self.parse_line(message)

	def motd(self):
		lines = open(config.MOTD).read().splitlines()
		for line in lines:
			self.send("ROOM (%s) %s\n" % (ts(), line))

	def parse_line(self, message):
		if message.startswith("USER "):
			self.ulogin = message[5:]
			self.parent.broadcast("JOIN %s\n" % self.ulogin)
			self.parent.broadcast("ROOM (%s) %s entered the room.\n" % (ts(), self.ulogin))
		if message.startswith("TALK "):
			message = message[5:]
			self.parent.broadcast("TALK (%s) %s: %s\n" % (ts(), self.ulogin, message))

class Server:
	def __init__(self):
		try:
			os.remove(config.PATH)
		except OSError:
			pass
		self.clients = {}

	def broadcast(self, message):
		for client in self.clients.values():
			client.send(message)

	def run(self):
		server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		server.bind(config.PATH)
		server.listen(1)
		server.setblocking(0)

		epoll = select.epoll()
		epoll.register(server.fileno(), select.EPOLLIN)

		try:
			while True:
				events = epoll.poll(1)
				for fileno, event in events:
					if fileno == server.fileno():
						connection, address = server.accept()
						connection.setblocking(0)
						epoll.register(connection.fileno(), select.EPOLLIN)
						guest = Client(self, connection)
						guest.motd()
						for client in self.clients.values():
							guest.send("JOIN %s\n" % client.ulogin)
						self.clients[connection.fileno()] = guest
					elif event & select.EPOLLHUP:
						epoll.unregister(fileno)
						self.clients[fileno].close()
						login = self.clients[fileno].ulogin
						del self.clients[fileno]
						self.broadcast("PART %s\n" % login)
						self.broadcast("ROOM (%s) %s left the room.\n" % (ts(), login))
					elif event & select.EPOLLIN:
						self.clients[fileno].recv()
		finally:
			epoll.unregister(server.fileno())
			epoll.close()
			server.close()

if __name__ == "__main__":
	Server().run()

