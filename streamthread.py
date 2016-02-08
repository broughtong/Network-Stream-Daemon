import threading
import time
import sys

class streamThread(threading.Thread):
	#Stream Thread
	#Checks all associated ports for input
	#Then writes data to output ports

	def __init__(self, exitQueue, ports):
		threading.Thread.__init__(self)

		self.exitQueue = exitQueue
		self.ports = ports

	def run(self):
		while True:
			#Checks to see if the thread should close
			running = ""
			try:
				running = self.exitQueue.get(False)
			except:
				#Exception is raised when queue is empty
				pass

			if running == "Stop":
				return
			else:
				#Normal running code:
				if len(self.ports) < 1:
					#Make sure that if the thread isn't doing anything it doens't consume too much CPU
					time.sleep(0.5)
				else:
					#Checks each port's thread for any incoming data
					for p in self.ports:
						data = ""
						try:
							data = p.portDataQueue.get(True, 0.5)
						except:
							pass

						if data != "":
							for o in self.ports:
								#Examines if any other ports in stream are accepting that data
								if o.portInfo.portStatus == "Running":
									if o.portInfo.portIO == "Output" or o.portInfo.portIO == "Input and Output":
										#Depending on how the port is configured, either writes the data or filters it then writes
										if o.portInfo.outfilterUsed == False:
											print "Sending to output"
											o.write(data)
										else:
											if o.portInfo.outfilterWhitelist == True:
												for string in o.portInfo.outfilterStrings:
													if o.portInfo.outfilterPosition == 1:
														if data.startswith(string):
															o.write(data)
															break
													elif o.portInfo.outfilterPosition == 2:
														string = string + '\n'
														if data.endswith(string):
															o.write(data)
															break
													elif o.portInfo.outfilterPosition == 3:
														if string in data:
															o.write(data)
															break	
											elif o.portInfo.outfilterBlacklist == True:
												onList = False
												for string in o.portInfo.outfilterStrings:
													if o.portInfo.outfilterPosition == 1:
														if data.startswith(string):
															onList = True
															break
													elif o.portInfo.outfilterPosition == 2:
														string = string + '\n'
														if data.endswith(string):
															onList = True
															break
													elif o.portInfo.outfilterPosition == 3:
														if string in data:
															onList = True
															break
													if onList == False:
														o.write(data)
