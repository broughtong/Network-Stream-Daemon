import socket
import time
import sys

myport = 10104
destip = ""
destport = 10105

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", myport))
s.settimeout(5)

while True:
	try:
		print "Received: " + s.recv(4096)
	except:
		try:
			s.connect((destip, destport))
		except:
			print sys.exc_info()

	time.sleep(0.5)
s.close()
