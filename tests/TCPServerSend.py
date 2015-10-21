import socket
import sys
import time

myport = 20202
destip = "localhost"
destport = 20203
con = ""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", myport))
s.listen(5)
s.settimeout(5)

counter = 0

while True:
	counter += 1

	data = str(counter) + " from port: " + str(myport)
	print "Sending: " + data

	try:
		con.send(data)
	except:
		try:
			con, add = s.accept()
		except:
			print "Error: " + str(sys.exc_info())

	time.sleep(2)	
s.close()

