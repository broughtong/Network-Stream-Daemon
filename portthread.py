import threading
import Queue
import time
import os

from classes import *

class portThread(threading.Thread):
	#Thread is created for each running port
	#Handles all read/write operations and handles the data

	def __init__(self, exitQueue, stream, port):
		threading.Thread.__init__(self)

		self.exitQueue = exitQueue
		self.writeQueue = port.portDataQueue
		self.stream = stream
		self.port = port

	def run(self):
		while True:
			#These variables are used to keep track of inactivity
			#This is then used to reduce CPU usage if not being used
			noInput = False
			noOutput = False

			try:
				#Checks to see if thread should stop
				running = self.exitQueue.get(False)
				if running == "Stop":
					return
			except Queue.Empty:
				#As it uses non-blocking calls, if the queue is empty, an 'empty' exception is raised
				#The thread expects the queue to be empty most of the time
				#Therefore, ignore this exception and carry on
				pass

			if self.stream.streamStatus == "Stopped":
				#Stream currently stopped
				#Sleep before checking if it has started
				time.sleep(0.5)
			else:
				if len(self.stream.streamPorts) < 2:
					#User might be attempting a simple echo
					if self.port.portInfo.portIO != "Input and Output":
						#This is the only port in the stream, so sleep until more join to save on CPU
						time.sleep(1)

				if self.port.portInfo.portIO != "Input":
					#Port is either output or 'input and output'
					#So must be a data output
					data = ""
					try:
						#Checks to see if any data to output has been received
						data = self.writeQueue.get(False)
					except Queue.Empty:
						#No data has been received
						noOutput = True

					if data != "":
						if self.port.portInfo.outfilterUsed == False:
							#If port isn't using a filter, write data
							print self.port.portInfo.portName + " write: " + data
							self.port.writePort(data)
						else:
							#If a filter is being used, check data
							if self.port.portInfo.outfilterWhitelist == True:
								#Whitelist filter, only allow data to be written if its on the list
								for line in self.port.portInfo.outfilterStrings:
									if self.port.portInfo.outfilterPosition == 1:
										#Search for string at the start of the data
										if data.startswith(line):
											self.port.writePort(data)
											break
									elif self.port.portInfo.outfilterPosition == 2:
										#Search for string at the end of the data
										#EOL is included in search 'endswith' function so must be appended
										line = line + os.linesep
										if data.endswith(line):
											self.port.writePort(data)
											break
									elif self.port.portInfo.outfilterPosition == 3:
										#Search for string anywhere in data
										if line in data:
											self.port.writePort(data)
											break

							elif self.port.portInfo.outfilterBlacklist == True:
								#Blacklist filter, allow all data except whats on the list
								onList = False

								for line in self.port.portInfo.outfilterStrings:
									if self.port.portInfo.outfilterPosition == 1:
										#Search for string at the start of the data
										if data.startswith(line):
											onList = True
											break
									elif self.port.portInfo.outfilterPosition == 2:
										#Search for string at the end of the data
										#EOL is included in search 'endswith' function so must be appended
										line = line + os.linesep
										if data.endswith(line):
											onList = True
											break
									elif self.port.portInfo.outfilterPosition == 3:
										#Search for string anywhere in data
										if line in data:
											onList = True
											break
								if onList != True:
									#If the data was not found on the list, then write it
									self.port.writePort(data)
					

				if self.port.portInfo.portIO != "Output":
					#Port is either input or 'input and output'
					#So must be a data input
					data = ""
					#Read the data in
					if self.port.portInfo.portType == "Serial Port":
						try:
							data = self.port.portHandle.read(2048)
						except:
							pass
					elif self.port.portInfo.portType == "Network Port":
						if self.port.portInfo.netUDP == True:
							try:
								data = self.port.portHandle.recv(4096)
							except:
								pass
						else:
							if self.port.portInfo.netServer == True:
								try:
									data = self.port.TCPHandle.recv(4096)
								except:
									try:
										self.port.TCPHandle, address = self.port.portHandle.accept()
									except:
										pass
							else:
								try:
									data = self.port.portHandle.recv(4096)
								except:
									try:
										self.port.portHandle.connect((self.portInfo.destIP, int(self.portInfo.destPort)))
									except:
										pass
					if data != "":
						if self.port.portInfo.infilterUsed == False:
							#If port isn't using a filter, write data
							for p in self.stream.streamPorts:
								if p.portInfo.portName == self.port.portInfo.portName:
									if self.port.portInfo.echo == True:
										p.portDataQueue.put(data)
								else:
									p.portDataQueue.put(data)
						else:
							#Port is using a filter
							if self.port.portInfo.infilterWhitelist == True:
								#Whitelist filter, only allow data to be written if its on the list
								onList = False
								for line in self.port.portInfo.infilterStrings:
									if self.port.portInfo.infilterPosition == 1:
										#Search for string at the start of the data
										if data.startswith(line):
											onList = True
											break
									elif self.port.portInfo.infilterPosition == 2:
										#Search for string at the end of the data
										#EOL is included in search 'endswith' function so must be appended
										line = line + os.linesep
										if data.endswith(line):
											onList = True
											break
									elif self.port.portInfo.infilterPosition == 3:
										#Search for string anywhere in data
										if line in data:
											onList = True
											break
								if onList == True:
									for p in self.stream.streamPorts:
										if p.portInfo.portName == self.portInfo.Name:
											if self.portInfo.echo == True:
												p.portDataQueue.put(data)
										else:
											p.portDataQueue.put(data)

							elif self.port.portInfo.infilterBlacklist == True:
								#Blacklist filter, allow all data except whats on the list
								onList = False
								for line in self.port.portInfo.infilterStrings:
									if self.port.portInfo.infilterPosition == 1:
										#Search for string at the start of the data
										if data.startswith(line):
											onList = True
											break
									elif self.port.portInfo.infilterPosition == 2:
										#Search for string at the end of the data
										#EOL is included in search 'endswith' function so must be appended
										line = line + os.linesep
										if data.endswith(line):
											onList = True
											break
									elif self.port.portInfo.infilterPosition == 3:
										#Search for string anywhere in data
										if line in data:
											onList = True
											break
								if onList != True:
									#If the data was not found on the list, then write it
									for p in self.stream.streamPorts:
										if p.portInfo.portName == self.portInfo.Name:
											if self.portInfo.echo == True:
												p.portDataQueue.put(data)
										else:
											p.portDataQueue.put(data)
					else:
						noInput = True
		
				if noInput == False or noOutput == False:
					#No port activity, so sleep to reduce CPU usage
					time.sleep(0.2)
