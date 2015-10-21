import socket
import time
import sys

myport = 12346
destip = "localhost"
destport = 12345

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(5)
s.bind(("", myport))

counter = 0

while True:
	counter += 1

	data = str(counter) + " from port: " + str(myport)
	print "Sending: " + data

	try:
		s.sendto(data,  (destip, destport))
	except:
		print "Error: " + str(sys.exc_info())

	time.sleep(2)

s.close()

