import socket
import time
import sys

myport = 12345

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	
s.bind(("", myport))

while True:
	try:
		print "Data received: " + s.recv(4096)
	except:
		print "Error reading port: " + str(sys.exc_info())
		time.sleep(0.5)
s.close()


