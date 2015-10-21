import socket
import time

myport = 20202
destip = "localhost"
destport = 20203
con = ""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", myport))
s.listen(5)
s.settimeout(5)

while True:
	try:
		data = con.recv(4096)
		print "Received: " + data
		con.send(data)
	except:
		try:
			con, add = s.accept()
		except:
			pass

	time.sleep(2)	
s.close()
