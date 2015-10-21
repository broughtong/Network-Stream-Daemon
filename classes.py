import Queue
import socket
import serial
import sys

from streamthread import *
from portthread import *

class Stream():
	#Class holding streams variables
	def __init__(self):
		self.streamName = ""
		self.streamStatus = "Stopped"
		self.streamPorts = []
		self.streamTreeRowRef = None

class PortInfo():
	#Class holding port configuration details
	#This has to be separate from port class itself
	#This is so that it can be processed by Python's Pickle module
	#And therefore must be separated for live port handles, queues, locks etc.
	def __init__(self):
		#Generic port information
		self.portName = ""
		self.portType = ""
		self.portIO = ""
		self.portStatus = "Stopped"		
		self.portTreeRowRef = None
		self.echo = False

		#Physical port information	
		self.portLocation = ""
		self.portBaudRate = ""
		self.portByteSize = ""
		self.portParity = ""
		self.portStopBits = ""
		self.portXonXoff = False
		self.portRtsCts = False
		self.portDsrdtr = False

		#Network port information
		self.netTCP = True
		self.netUDP = False
		self.netServer = True
		self.netClient = False
		self.netPort = "9999"
		self.destIP = "127.0.0.1"
		self.destPort = "10000"

		#File port information
		self.fileLocation = ""
		self.fileWA = "a"
		#FileWA = Write/Append

		#In-Filter Settings
		self.infilterUsed = False
		self.infilterBlacklist = False
		self.infilterWhitelist = False
		self.infilterPosition = 1
		self.infilterStrings = []

		#Out-Filter Settings
		self.outfilterUsed = False
		self.outfilterBlacklist = False
		self.outfilterWhitelist = False
		self.outfilterPosition = 1
		self.outfilterStrings = []

class Port():
	#Class containing the actual live ports/queue/locks

	def __init__(self):
		#Contains port configuration properties
		self.portInfo = PortInfo()

		#Queue for inter-thread communication
		self.portExitQueue = Queue.Queue()
		self.portDataQueue = Queue.Queue()

		#Ports thread
		self.portThread = ""

		#Handle to port		
		self.portHandle = ""

		#Handle to TCP connection
		self.TCPHandle = ""	

	def openPort(self, stream):
		#When called opens the port/socket
		if self.portInfo.portType == "Serial Port":
			self.portHandle = serial.Serial()
			self.portHandle.port = self.portInfo.portLocation
			self.portHandle.baudrate = self.portInfo.portBaudRate
			
			if self.portInfo.portByteSize == "5":
				self.portHandle.bytesize = serial.FIVEBITS
			elif self.portInfo.portByteSize == "6":
				self.portHandle.bytesize = serial.SIXBITS
			elif self.portInfo.portByteSize == "7":
				self.portHandle.bytesize = serial.SEVENBITS
			elif self.portInfo.portByteSize == "8":
				self.portHandle.bytesize =  serial.EIGHTBITS

			if self.portInfo.portParity == "None":
				self.portHandle.parity = serial.PARITY_NONE
			elif self.portInfo.portParity == "Even":
				self.portHandle.parity = serial.PARITY_EVEN
			elif self.portInfo.portParity == "Odd":
				self.portHandle.parity = serial.PARITY_ODD
			elif self.portInfo.portParity == "Mark":
				self.portHandle.parity =  serial.PARITY_MARK
			elif self.portInfo.portParity == "Space":
				self.portHandle.parity =  serial.PARITY_SPACE

			if self.portInfo.portStopBits == "1":
				self.portHandle.stopbits = serial.STOPBITS_ONE
			elif self.portInfo.portStopBits == "1.5":
				self.portHandle.stopbits = serial.STOPBITS_ONE_POINT_FIVE
			elif self.portInfo.portStopBits == "2":
				self.portHandle.stopbits = serial.STOPBITS_TWO

			self.portHandle.xonxoff = self.portInfo.portXonXoff
			self.portHandle.rtscts = self.portInfo.portRtsCts
			self.portHandle.dsrdtr = self.portInfo.portDsrdtr
			self.portHandle.timeout = 0
			self.portHandle.writeTimeout = .5
			self.portHandle.interCharTimeout = .5

			try:
				self.portHandle.open()
			except:
				return sys.exc_info()

		elif self.portInfo.portType == "Network Port":
			if self.portInfo.netTCP == True:
				if self.portInfo.netServer == True:
					try:
						self.portHandle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						self.portHandle.bind(("", int(self.portInfo.netPort)))
						self.portHandle.settimeout(8)
						self.portHandle.listen(5)
					except:
						return sys.exc_info()
				else:
					try:
						self.portHandle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						self.portHandle.bind(("", int(self.portInfo.netPort)))
						self.portHandle.settimeout(5)
						self.portHandle.connect((self.portInfo.destIP, int(self.portInfo.destPort)))
					except:
						return sys.exc_info()
			elif self.portInfo.netUDP == True:
				try:
					self.portHandle = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
					self.portHandle.settimeout(2)
					self.portHandle.bind(("", int(self.portInfo.netPort)))
				except:
					return sys.exc_info()

		elif self.portInfo.portType == "File":
			try:
				self.portHandle = open(self.portInfo.fileLocation, self.portInfo.fileWA, 0)
			except:
				return sys.exc_info()

		self.portThread = portThread(self.portExitQueue, stream, self)
		self.portThread.start()
		self.portInfo.portStatus = "Running"
		return True

	def writePort(self, data):
		#Writes data to this port

		if self.portInfo.portType == "Serial Port":
			try:
				self.portHandle.write(data)
			except:
				pass
		elif self.portInfo.portType == "Network Port":
			if self.portInfo.netUDP == True:
				try:
					#Attempts to send data to host
					self.portHandle.sendto(data, (self.portInfo.destIP, int(self.portInfo.destPort)))
				except:
					#Port currently not available to send
					print sys.exc_info()
			elif self.portInfo.netTCP == True:
				if self.portInfo.netServer == True:
					try:
						#Send data to connected IP
						self.TCPHandle.send(data)
					except:
						print sys.exc_info()
						#No connected host
						try:
							#Try to reconnect
							self.TCPHandle, address = self.portHandle.accept()
						except:
							print sys.exc_info()
							pass
				else:
					try:
						self.portHandle.send(data)
					except:
						self.portHandle.connect((self.portIndo.destIP, int(self.portInfo.destPort)))
						
		else:
			#File
			try:
				#Write data to file
				self.portHandle.write(data)
			except:
				#File currently unavailable
				pass

	def closePort(self):
		#Closes port/socket
		self.portExitQueue.put("Stop")
		self.portInfo.portStatus = "Stopped"

		if self.portInfo.portType == "Serial Port":
			try:
				self.portHandle.close()
			except:
				pass
		elif self.portInfo.portType == "Network Port":
			try:
				self.portHandle.shutdown(SHUT_RDWR)
				self.portHandle.close()
			except:
				pass
		elif self.portInfo.portType == "File":
			try:
				self.portHandle.close()
			except:
				pass

		self.TCPHandle = ""
		self.portThread = ""
		self.portHandle = ""
