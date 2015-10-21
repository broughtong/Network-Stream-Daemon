import socket
import time
import sys

myport = 8081
destip = ""
destport = 8080

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", myport))
s.settimeout(5)

counter = 0

while True:
	counter += 1

	data = str(counter) + " from port: " + str(myport)
	print "Sending: " + data

	try:
		s.send(data)
		data = s.recv(4096)
		print "Received: " + data
	except:
		try:
			s.connect((destip, destport))
		except:
			print "Error: " + str(sys.exc_info())

	time.sleep(0.5)
s.close()
