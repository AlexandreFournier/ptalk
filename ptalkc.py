#!/usr/bin/python

import socket, curses, sys, os, traceback, select
import config

LOGIN = os.getenv("PTALK_LOGIN")

def ts():
        import time
        return time.strftime("%H:%M:%S", time.gmtime())

class Header:
	def __init__(self, parent):
		self.parent = parent
		lines, cols = self.lc(); x, y = self.xy()
		self.window = parent.subwin(lines, cols, x, y)
		self.window.bkgd(' ', curses.color_pair(4))
		self.buffer = ""

	def xy(self):
		y, x = self.parent.getmaxyx()
		return 0, 0

	def lc(self):
		y, x = self.parent.getmaxyx()
		return 1, x

	def text(self, line):
		self.buffer = line
		self.refresh()

	def resize(self):
		pass

	def refresh(self):
		self.buffer = "(%s) info :: scroll-up/down" % ts()
		self.window.move(0,0)
		self.window.deleteln()
		self.window.addstr(0, 0, self.buffer)
		self.window.refresh()

class Dialog:

	HISTORY = config.HISTORY

	def __init__(self, parent):
		self.parent = parent
		lines, cols = self.lc(); x, y = self.xy()
		self.window = parent.subwin(lines, cols, x, y)
		self.padwin = curses.newpad(Dialog.HISTORY, cols)
		self.window.bkgd(' ', curses.color_pair(2))
		self.padwin.bkgd(' ', curses.color_pair(2))
		self.offset = 0
		self.scroll = 0
	
	def scroll_up(self):
		lines, cols = self.lc()
		self.scroll = self.scroll - lines + 3;
		self.scroll = max(self.scroll, 0)
		self.refresh()
	
	def scroll_down(self):
		lines, cols = self.lc()
		self.scroll = self.scroll + lines - 3;
		self.scroll = min(self.scroll, Dialog.HISTORY - 1)
		self.refresh()

	def write_line(self, line, pair = 2):
		self.padwin.addstr(self.offset, 0, line, curses.color_pair(pair))
		if self.offset < Dialog.HISTORY - 1:
			self.offset += 1
		else:
			self.padwin.move(0,0)
			self.padwin.deleteln()
		self.refresh()

	def xy(self):
		return 1, 0

	def lc(self):
		y, x = self.parent.getmaxyx()
		return y - 3, x - 1 - 16

	def resize(self):
		pass

	def refresh(self):
		lines, cols = self.lc()
		self.window.refresh()
		self.padwin.refresh(self.scroll, 0, 1, 0, lines, cols)

class People:
	def __init__(self, parent):
		self.parent = parent
		self.people = []
		lines, cols = self.lc(); x, y = self.xy()
		self.window = parent.subwin(lines, cols, x, y)
	
	def add_person(self, person):
		self.people.append(person)
		self.people.sort()
		self.refresh()
	
	def del_person(self, person):
		self.people.remove(person)
		self.refresh()
	
	def xy(self):
		x, y = self.parent.getmaxyx()
		return 1, y - 16

	def lc(self):
		y, x = self.parent.getmaxyx()
		return y - 3, 16 

	def resize(self):
		pass

	def refresh(self):
		self.window.bkgd(' ', curses.color_pair(2))
		self.window.erase()
		for i,person in enumerate(self.people):
			self.window.addstr(i, 1, person)
		self.window.refresh()

class Status:
	def __init__(self, parent):
		self.parent = parent
		lines, cols = self.lc(); x, y = self.xy()
		self.window = parent.subwin(lines, cols, x, y)
		self.window.bkgd(' ', curses.color_pair(4))
		self.buffer = ""

	def xy(self):
		y, x = self.parent.getmaxyx()
		return y - 2, 0

	def lc(self):
		y, x = self.parent.getmaxyx()
		return 1, x

	def text(self, line):
		self.buffer = line
		self.refresh()

	def resize(self):
		pass

	def refresh(self):
		self.window.move(0,0)
		self.window.deleteln()
		self.window.addstr(0, 0, self.buffer)
		self.window.refresh()

class Prompt:
	def __init__(self, parent):
		self.parent = parent
		lines, cols = self.lc(); x, y = self.xy()
		self.window = parent.subwin(lines, cols, x, y)
		self.window.bkgd(' ', curses.color_pair(5))
		self.buffer = ""

	def putchar(self, ch):
		try:
			self.buffer += ch
			self.refresh()
		except Exception, e:
			if config.DEBUG:
				raise Exception("cannot append '%0.2X' to string" % ch)

	def message(self):
		message = self.buffer
		self.window.move(0,0)
		self.buffer = ""
		self.refresh()
		return message

	def backspace(self):
		if len(self.buffer) == 0:
			return
		self.buffer = self.buffer[0:-1]
		self.refresh()

	def xy(self):
		x, y = self.parent.getmaxyx()
		return x - 1, 0

	def lc(self):
		x, y = self.parent.getmaxyx()
		return 1, y

	def resize(self):
		pass

	def refresh(self):
		self.window.move(0,0)
		self.window.deleteln()
		self.window.addstr(0, 0, "status> %s" % self.buffer)
		self.window.refresh()

class Main:
	def __init__(self, window):
		self.window = window
		self.window.bkgd(' ', curses.color_pair(1))
		self.header = Header(window)
		self.dialog = Dialog(window)
		self.people = People(window)
		self.status = Status(window)
		self.prompt = Prompt(window)
		self.buffer = ""

		curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLUE)
		curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
		curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)
		curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
		curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
		curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)

		self.height, self.width = self.window.getmaxyx()
		self.refresh()

	def recv(self):
		try:
			self.buffer += self.client.recv(1024)
			messages = self.buffer.splitlines()
			if self.buffer.endswith("\n"):
				self.buffer = ""
			else:
				self.buffer = messages.pop()
			for message in messages:
				self.parse_line(message)
		except Exception, e:
			pass

	def parse_line(self, message):
		if message.startswith("TALK "):
			self.dialog.write_line(message[5:])
		elif message.startswith("ROOM "):
			self.dialog.write_line(message[5:], 6)
		elif message.startswith("JOIN "):
			self.people.add_person(message[5:])
		elif message.startswith("PART "):
			self.people.del_person(message[5:])
		
	def run(self):
		self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.client.connect(config.PATH)
		self.client.send("USER %s\n" % LOGIN)

		while True:
			infds, outfds, exfds = select.select([self.client, 0], [], [])

			if self.client in infds:
				self.recv()
			
			if 0 in infds:
				c = self.window.getch()
				if c in (curses.KEY_RESIZE, -1):
					self.height, self.width = window.getmaxyx()
					self.resize()
					self.refresh()
					continue
				if c in (curses.KEY_ENTER, 10):
					message = self.prompt.message()
					self.client.send("TALK %s\n" % message)
					continue
				if c == curses.KEY_BACKSPACE:
					self.prompt.backspace()
					continue
				if c == curses.KEY_NPAGE:
					self.dialog.scroll_down()
					continue
				if c == curses.KEY_PPAGE:
					self.dialog.scroll_up()
					continue

				if c < 256:
					c = chr(c)
					self.prompt.putchar(c)

	def resize(self):
		self.header.resize()
		self.dialog.resize()
		self.people.resize()
		self.status.resize()
		self.prompt.resize()

	def refresh(self):
		y, x = self.window.getmaxyx()
		self.window.vline(1, x - 16 - 1, '|', y - 1)
		self.window.refresh()
		self.header.refresh()
		self.dialog.refresh()
		self.people.refresh()
		self.status.refresh()
		self.prompt.refresh()

if __name__ == '__main__':
	try:
		window = curses.initscr()
		curses.noecho()
		curses.curs_set(0)
		curses.cbreak()
		curses.start_color()
		window.keypad(1)
		Main(window).run()

	except:
		pass
	#window.keypad(0)
	curses.echo()
	curses.nocbreak()
	curses.curs_set(1)
	curses.endwin()
	if config.DEBUG:
		traceback.print_exc()
