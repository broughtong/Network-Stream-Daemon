import os
import platform
import pickle
import serial
import socket
import Queue
import threading
import time
import gtk
import copy

#Inform gtk that threads will be used
gtk.gdk.threads_init()

if os.environ.get('DESKTOP_SESSION') == 'ubuntu':
	
	import appindicator

from classes import *

#gobject.threads_init()

streamList = []

#The stream list is filled with an example stream and port
#These are overwritten if settings from a previous setting are found
exampleStream = Stream()
exampleStream.streamName = "Example Stream"
exampleStream.streamIndex = 0
exampleStream.streamRunning = False
streamList.append(exampleStream)

examplePort = Port()
examplePort.portInfo.portName = "Example Port"
examplePort.portInfo.portType = "Network Port"
examplePort.portInfo.portIO = "Input"
examplePort.portInfo.netTCP = True
examplePort.portInfo.netUDP = False
examplePort.portInfo.netServer = True
examplePort.portInfo.netClient = False
examplePort.portInfo.netPort = "12345"
examplePort.portInfo.destIP = "localhost"
examplePort.portInfo.destPort = "12346"
exampleStream.streamPorts.append(examplePort)

examplePort = Port()
examplePort.portInfo.portName = "Example Port 2"
examplePort.portInfo.portType = "Network Port"
examplePort.portInfo.portIO = "Output"
examplePort.portInfo.netTCP = True
examplePort.portInfo.netUDP = False
examplePort.portInfo.netServer = True
examplePort.portInfo.netClient = False
examplePort.portInfo.netPort = "12347"
examplePort.portInfo.destIP = "localhost"
examplePort.portInfo.destPort = "12348"
exampleStream.streamPorts.append(examplePort)

class wn_system_tray():
	#System Tray class

	def __init__(self):

		self.tray = None #Handle to system tray object
		self.aboutWindow = None #Handle to about window
		self.aboutOpen = False #If about window is open
		self.configureWindow = None #Handle to configure window
		self.configureOpen = False #If configure window is open

		if os.environ.get('DESKTOP_SESSION') == 'ubuntu':

			#Running unity desktop environment, so use AppIndicator for system tray

			self.tray = appindicator.Indicator("Port Router", '/home/george/Downloads/BRO11239330_CMP3060M/logo.png', appindicator.CATEGORY_APPLICATION_STATUS)
			self.tray.set_status(appindicator.STATUS_ACTIVE)

			self.cb_show_menu(None, None, None)

		elif os.environ.get('DESKTOP_SESSION') == 'gnome':

			#Running Gnome based linux distribution, such as fedora, so use default gtk system tray

			self.tray = gtk.StatusIcon()
			self.tray.set_from_file('logo.png')
			self.tray.set_tooltip("Port Router")
                	self.tray.connect('popup-menu', self.cb_show_menu)
                	self.tray.connect('activate', self.cb_show_menu, 0, 0)

		elif platform.system() == 'Windows':

			#Running windows, so use default gtk system tray

			self.tray = gtk.StatusIcon()
			self.tray.set_from_file('logo2.png')
			self.tray.set_tooltip("Port Router")
                	self.tray.connect('popup-menu', self.cb_show_menu)
                	self.tray.connect('activate', self.cb_show_menu, 0, 0)

		else:

			#Running unsupported non-windows, non-unity, non-gnome desktop environment

			md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "The current Operating System/Desktop Environment is not supported")
			md.set_position(gtk.WIN_POS_CENTER)                             
			md.run()
                        md.destroy()

        def cb_show_menu(self, icon, button, time):

                #When the user has clicked the system tray icon, menu is created and drawn next to icon

		#Creates Menu Items                        
                self.menu = gtk.Menu()

                menuItem = gtk.MenuItem("Configure")
                menuItem.connect('activate', self.cb_configure)
                self.menu.append(menuItem)

                menuItem = gtk.MenuItem("Help")
                menuItem.connect('activate', self.cb_about)
                self.menu.append(menuItem)

                menuItem = gtk.MenuItem("About")
                menuItem.connect('activate', self.cb_about)
                self.menu.append(menuItem)
                
                menuItem = gtk.MenuItem("Exit")
                menuItem.connect("activate", self.cb_exit)
                self.menu.append(menuItem)

                self.menu.show_all()

                if os.environ.get('DESKTOP_SESSION') == 'ubuntu':

	                #AppIndicator way of adding the menu to the system tray

                        self.tray.set_menu(self.menu)

               	else:
                	#Non AppIndicator way of adding the menu to the system tray

                        self.menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.tray)

        def cb_configure(self, widget):
                #Checks if configure window is open, if so focuses it, otherwise opens new configure window

                if self.configureWindow == None:

                        self.configureWindow = wn_configure()

                else:

                        if self.configureWindow.running == True:

                                self.configureWindow.window.present_with_time(int(time.time()))
                                self.configureWindow.window.window.focus()

                        else:                       

                                self.configureWindow = wn_configure()

        def cb_about(self, widget):
                #Used to test if about window is already open before opening another
                #If one is already open, it focuses it, otherwise opens another
                if self.aboutOpen == False:

                        self.aboutOpen = True

                        self.aboutWindow = wn_about()
                        self.aboutWindow.aboutdialog.run()
                        self.aboutWindow.aboutdialog.destroy()
                        
                        self.aboutOpen = False

                else:

                        self.aboutWindow.aboutdialog.present_with_time(int(time.time()))
                        self.aboutWindow.aboutdialog.window.focus()

	def cb_exit(self, widget):

                #If system tray is closed, make sure GTK and windows are as well

		#Instructs all ports and streams to stop
		for s in streamList:

			for p in s.streamPorts:

				p.closePort()

                if self.aboutOpen == True:

			#As Gtk runs about windows in another thread
			#It must be manually closed
                        self.aboutWindow.aboutdialog.destroy()

		#Close Gtk
		gtk.main_quit()

class wn_about():
	#About window creation

	def __init__(self):

		self.aboutdialog = gtk.AboutDialog()
                self.aboutdialog.set_position(gtk.WIN_POS_CENTER)
		self.aboutdialog.set_name("Port Router")
		self.aboutdialog.set_version("0.01")
		self.aboutdialog.set_comments("Cross Platform Port Router written by George Broughton")
		self.aboutdialog.set_authors(["Project programmed by George Broughton\nSupervised by Dr Georgios Tzimiropoulos"])

class wn_configure():
	#This class creates the configuration window
	#It also contains all associated widget callbacks

	def __init__(self):
		
		self.running = True #Used by the system tray to keep track of the window status
		self.editing = "" #Used to tell if a port is being edited

		#Window creation code
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_position(gtk.WIN_POS_CENTER)
		self.window.set_size_request(450, 300)
		self.window.set_title("Configure")
		self.window.set_border_width(8)
		self.window.set_resizable(True)
		self.window.connect("delete_event", self.cb_close_window)

		self.treeStore = gtk.TreeStore(str, str, str, str)
		self.buildTree()

		windowvbox = gtk.VBox(False, 0)

		scrolledWindow = gtk.ScrolledWindow()
		scrolledWindow.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		self.tree = gtk.TreeView(self.treeStore)
		self.tree.set_rules_hint(True)
		scrolledWindow.add(self.tree)

		self.createColumns(self.tree)

		windowvbox.pack_start(scrolledWindow, True, True, 0)

		buttonhbox = gtk.HBox(False, 0)

		but_AS = gtk.Button("Add Stream")
		but_AS.connect("clicked", self.cb_but_add_stream)
		buttonhbox.pack_start(but_AS, False, False, 0)

		but_AP = gtk.Button("Add Port")
		but_AP.connect("clicked", self.cb_but_add_port)
		buttonhbox.pack_start(but_AP, False, False, 0)

		but_edit = gtk.Button("Edit")
		but_edit.connect("clicked", self.cb_but_edit)
		buttonhbox.pack_start(but_edit, False, False, 0)

		but_remove = gtk.Button("Remove")
		but_remove.connect("clicked", self.cb_but_remove)
		buttonhbox.pack_start(but_remove, False, False, 0)

		but_start_stop = gtk.Button("Start/Stop")
		but_start_stop.connect("clicked", self.cb_but_start_stop)
		buttonhbox.pack_end(but_start_stop, False, False, 0)

		windowvbox.pack_start(buttonhbox, False, False, 0)

		self.window.add(windowvbox)
		self.window.show_all()

	def cb_close_window(self, widget, button):
		#Used to inform the system tray the window has closed
                self.running = False

	def buildTree(self):
		#Builds the tree(table) from the configure window
		#Note: Should NOT be used for refreshing tree as this causes currently open drop downs to close

		global streamList

		self.treeStore.clear()

		for s in streamList:

			parentStream = self.treeStore.append(None, [s.streamName, s.streamStatus, '', ''])
			s.streamTreeRowRef = gtk.TreeRowReference(self.treeStore, self.treeStore.get_path(parentStream))

			for p in s.streamPorts:

				rowiter = self.treeStore.append(parentStream, [p.portInfo.portName, p.portInfo.portStatus, p.portInfo.portIO, p.portInfo.portType]) 
				p.portInfo.portTreeRowRef = gtk.TreeRowReference(self.treeStore, self.treeStore.get_path(rowiter))

	def createColumns(self, treeView):
		#Create columns for treeview object(ie. the table in the configure window)
    
		rendererText = gtk.CellRendererText()
		column = gtk.TreeViewColumn("Name", rendererText, text=0)
		column.set_sort_column_id(0) 
		column.set_resizable(True)   
		treeView.append_column(column)
		
		rendererText = gtk.CellRendererText()
		column = gtk.TreeViewColumn("Status", rendererText, text=1)
		column.set_sort_column_id(1)
		column.set_resizable(True) 
		treeView.append_column(column)

		rendererText = gtk.CellRendererText()
		column = gtk.TreeViewColumn("Input/Output", rendererText, text=2)
		column.set_sort_column_id(2)
		column.set_resizable(True) 
		treeView.append_column(column)

		rendererText = gtk.CellRendererText()
		column = gtk.TreeViewColumn("Type", rendererText, text=3)
		column.set_sort_column_id(3)
		column.set_resizable(True) 
		treeView.append_column(column)

	def cb_but_add_stream(self, widget):
		#Add stream button clicked, open window to prompt user for stream name
		self.addstream = wn_add_stream()
		self.addstream.window.set_transient_for(self.window)
		self.addstream.but_acc.connect("clicked", self.cb_add_stream_but_acc)

	def cb_add_stream_but_acc(self, widget):
		#Accept button pressed on the add stream window

		global streamList

		#Check they have actually entered a name
                if len(self.addstream.nameEntry.get_text()) == 0:

                        md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please enter a stream name")
			md.set_position(gtk.WIN_POS_CENTER)
			md.set_transient_for(self.addstream.window)			
			md.run()
			md.destroy()
			return

		#Check name isn't already in use
		for s in streamList:
			if self.addstream.nameEntry.get_text() == s.streamName:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Stream name already in use")
				md.set_position(gtk.WIN_POS_CENTER)                                
				md.run()
                                md.destroy()
                                return                               

		#Add new stream
		s = Stream()
		s.streamName = self.addstream.nameEntry.get_text()
		streamList.append(s)

		#Update GUI
		rowiter = self.treeStore.append(None, [self.addstream.nameEntry.get_text(), 'Stopped', '', ''])
		s.streamTreeRowRef = gtk.TreeRowReference(self.treeStore, self.treeStore.get_path(rowiter))
		self.addstream.window.destroy()
		saveSettings()	

	def cb_but_add_port(self, widget):
		#Add port button clicked in configure window

		global streamList

		#Ignore if there is no stream to add to
		if len(streamList) == 0:

			md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "A stream must be added before ports can be.")
			md.set_position(gtk.WIN_POS_CENTER)
			md.set_transient_for(self.window)
			md.run()
			md.destroy()

		else:

			#Launch Add port window
			self.addport = wn_port()
			self.addport.window.set_transient_for(self.window)
			self.addport.but_acc.connect("clicked", self.cb_add_port_but_acc)

	def cb_add_port_but_acc(self, widget):
		#New port added

		global streamList

		#Checks if configuration is valid
		if self.cb_check_input() == False:

			return

		newPort = PortInfo()

		newPort.portName = self.addport.entry_name.get_text()
		newPort.portType = self.addport.combo_type.get_active_text()
		newPort.portStatus = "Stopped"
		newPort.portIO = self.addport.combo_rw.get_active_text()

		newPort.echo = self.addport.includeSelf.get_active()

		newPort.portLocation = self.addport.entry_port.get_text()
		newPort.portBaudRate = self.addport.entry_baud.get_text()
		newPort.portByteSize = self.addport.combo_bytesize.get_active_text()
		newPort.portParity = self.addport.combo_parity.get_active_text()
		newPort.portStopBits = self.addport.combo_stopbits.get_active_text()
		newPort.portXonXoff = self.addport.check_x.get_active()
		newPort.portRtsCts = self.addport.check_rtscts.get_active()
		newPort.portDsrdtr = self.addport.check_dsrdtr.get_active()
				
		newPort.netPort = self.addport.netPort.get_text()
		newPort.destIP = self.addport.destIP.get_text()
		newPort.destPort = self.addport.destPort.get_text()
		
		if self.addport.netTCP.get_active() == True:

			newPort.netUDP = False
			newPort.netTCP = True

		elif self.addport.netUDP.get_active() == True:

			newPort.netUDP = True
			newPort.netTCP = False

		if self.addport.netServer.get_active() == True:

			newPort.netClient = False
			newPort.netServer = True

		elif self.addport.netClient.get_active() == True:

			newPort.netClient = True
			newPort.netServer = False
		
		newPort.fileLocation = self.addport.FilePathEntry.get_text()

		if self.addport.fileAppend.get_active() == True:

			newPort.fileWA = "a"

		elif self.addport.fileOverwrite.get_active() == True:

			newPort.fileWA = "w"

		if self.addport.infilteron.get_active() == True:

			newPort.infilterUsed = True

			if self.addport.infilterBlacklist.get_active() == True:

				newPort.infilterBlacklist = True

			else:

				newPort.infilterWhitelist = True

			if self.addport.infilterStart.get_active() == True:

				newPort.infilterPosition = 1

			elif self.addport.infilterEnd.get_active() == True:

				newPort.infilterPosition = 2

			elif self.addport.infilterAnywhere.get_active() == True:

				newPort.infilterPosition = 3

			textbuffer = self.addport.infilterText.get_buffer()
			
			text = textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter())	
			newPort.infilterStrings = text.split(os.linesep)
			newPort.infilterStrings = filter(None, newPort.infilterStrings)

		if self.addport.outfilteron.get_active() == True:

			newPort.outfilterUsed = True

			if self.addport.outfilterBlacklist.get_active() == True:

				newPort.outfilterBlacklist = True

			else:

				newPort.outfilterWhitelist = True

			if self.addport.outfilterStart.get_active() == True:

				newPort.outfilterPosition = 1

			elif self.addport.outfilterEnd.get_active() == True:

				newPort.outfilterPosition = 2

			elif self.addport.outfilterAnywhere.get_active() == True:

				newPort.outfilterPosition = 3

			textbuffer = self.addport.outfilterText.get_buffer()
			
			text = textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter())	
			newPort.outfilterStrings = text.split(os.linesep)
			newPort.outfilterStrings = filter(None, newPort.outfilterStrings)

		sname = self.addport.combo_stream.get_active_text()

		port = Port()
		port.portInfo = newPort

		#Add the port to its stream
		for s in streamList:

			if s.streamName == sname:

				s.streamPorts.append(port)
				rowpath = s.streamTreeRowRef.get_path()
				rowiter = self.treeStore.append(self.treeStore.get_iter(rowpath), [newPort.portName, newPort.portStatus, newPort.portIO, newPort.portType])
				newPort.portTreeRowRef = gtk.TreeRowReference(self.treeStore, self.treeStore.get_path(rowiter))
				break

		self.addport.window.destroy()		
		saveSettings()

	def cb_but_edit(self, widget):
		#Edit button pressed

		global streamList

		if self.tree.get_cursor()[0] == None: #nothing selected

			return

		else:

			if len(self.tree.get_cursor()[0]) == 1: #stream selected

				self.addstream = wn_add_stream()
				self.addstream.window.set_transient_for(self.window)
				rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
				rowref = gtk.TreeRowReference(self.treeStore, self.treeStore.get_path(rowiter))
				for s in streamList:
					path = s.streamTreeRowRef.get_path()
					if self.treeStore.get_path(rowiter) == path:
						self.addstream.nameEntry.set_text(str(s.streamName))
				self.addstream.but_acc.connect("clicked", self.cb_edit_stream_but_acc)

			else: #port selected

				p = []

				#Get selected port
				rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
				rowpath = self.treeStore.get_path(rowiter)
				parent = ""

				for s in streamList:
					for i in s.streamPorts:
						path = i.portInfo.portTreeRowRef.get_path()
						if path == rowpath:
							p = i
							parent = s
							break

				i = 0

				self.addport = wn_port()
				self.addport.window.set_transient_for(self.window)
				self.addport.entry_name.set_text(p.portInfo.portName)

				self.addport.includeSelf.set_active(p.portInfo.echo)
				
				for s in xrange(0, len(streamList)):
					if streamList[s].streamName == parent.streamName:
						self.addport.combo_stream.set_active(s)
				
				if p.portInfo.portType == "Serial Port":
					i = 0
				elif p.portInfo.portType == "Network Port":
					i = 1
				elif p.portInfo.portType == "File":
					i = 2

				self.addport.combo_type.set_active(i)
				
				if p.portInfo.portType == "File":
					i = 0
				else:
					if p.portInfo.portIO == "Input":
						i = 0
					elif p.portInfo.portIO == "Output":
						i = 1
					elif p.portInfo.portIO == "Input and Output":
						i = 2

				self.addport.combo_rw.set_active(i)
				self.addport.entry_port.set_text(p.portInfo.portLocation)
				self.addport.entry_baud.set_text(p.portInfo.portBaudRate)
				
				if p.portInfo.portByteSize == "5":
					i = 0
				elif p.portInfo.portByteSize == "6":
					i = 1
				elif p.portInfo.portByteSize == "7":
					i = 2
				elif p.portInfo.portByteSize == "8":
					i = 3

				self.addport.combo_bytesize.set_active(i)
				
				if p.portInfo.portParity == "None":
					i = 0
				elif p.portInfo.portParity == "Even":
					i = 1
				elif p.portInfo.portParity == "Odd":
					i = 2
				elif p.portInfo.portParity == "Mark":
					i = 3
				elif p.portInfo.portParity == "Space":
					i = 4

				self.addport.combo_parity.set_active(i)

				if p.portInfo.portStopBits == "1":
					i = 0
				elif p.portInfo.portStopBits == "1.5":
					i = 1
				elif p.portInfo.portStopBits == "2":
					i = 2

				self.addport.combo_stopbits.set_active(i)
				self.addport.check_x.set_active(p.portInfo.portXonXoff)
				self.addport.check_rtscts.set_active(p.portInfo.portRtsCts)
				self.addport.check_dsrdtr.set_active(p.portInfo.portDsrdtr)
				self.addport.netTCP.set_active(p.portInfo.netTCP)
				self.addport.netUDP.set_active(p.portInfo.netUDP)
				self.addport.netServer.set_active(p.portInfo.netServer)
				self.addport.netClient.set_active(p.portInfo.netClient)
				self.addport.netPort.set_text(p.portInfo.netPort)
				self.addport.destIP.set_text(p.portInfo.destIP)
				self.addport.destPort.set_text(p.portInfo.destPort)
				self.addport.FilePathEntry.set_text(p.portInfo.fileLocation)
				if p.portInfo.fileWA == "w":
					self.addport.fileOverwrite.set_active(True)
				elif p.portInfo.fileWA == "a":
					self.addport.fileAppend.set_active(True)

				self.addport.infilteron.set_active(p.portInfo.infilterUsed)
				self.addport.infilterWhitelist.set_active(p.portInfo.infilterWhitelist)
				self.addport.infilterBlacklist.set_active(p.portInfo.infilterBlacklist)

				if p.portInfo.infilterPosition == 1:
					self.addport.infilterStart.set_active(True)
				elif p.portInfo.infilterPosition == 2:
					self.addport.infilterEnd.set_active(True)
				elif p.portInfo.infilterPosition == 3:
					self.addport.infilterAnywhere.set_active(True)

				textbuffer = self.addport.infilterText.get_buffer()
				textbuffer.set_text(''.join(p.portInfo.infilterStrings))

				self.addport.outfilteron.set_active(p.portInfo.outfilterUsed)
				self.addport.outfilterWhitelist.set_active(p.portInfo.outfilterWhitelist)
				self.addport.outfilterBlacklist.set_active(p.portInfo.outfilterBlacklist)

				if p.portInfo.outfilterPosition == 1:
					self.addport.outfilterStart.set_active(True)
				elif p.portInfo.outfilterPosition == 2:
					self.addport.outfilterEnd.set_active(True)
				elif p.portInfo.outfilterPosition == 3:
					self.addport.outfilterAnywhere.set_active(True)
				
				textbuffer = self.addport.outfilterText.get_buffer()
				textbuffer.set_text(''.join(p.portInfo.outfilterStrings))
				
				self.addport.but_acc.connect("clicked", self.cb_edit_port_but_acc)

	def cb_edit_stream_but_acc(self, widget):
		#Stream name Edited

		global streamList

		newName = str(self.addstream.nameEntry.get_text())
		rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
		for s in streamList:
			path = s.streamTreeRowRef.get_path()
			if path == self.treeStore.get_path(rowiter):
				oldName = str(s.streamName)

		#No change in name, so make no changes
		if oldName == newName:
			
			self.addstream.window.destroy()
			return

		#Check if new name already exists before carrying on
		for s in streamList:
			if s.streamName == newName:
				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "New stream name already in use")
				md.set_position(gtk.WIN_POS_CENTER) 
				md.set_transient_for(self.addstream)                               
				md.run()
		                md.destroy()

				return

		#Update stream name
		for s in streamList:
			if s.streamName == oldName:
				s.streamName = newName

		#Update GUI
		self.treeStore.set_value(rowiter, 0, newName)
		self.addstream.window.destroy()
		saveSettings()	

	def cb_edit_port_but_acc(self, widget):
		#Port has been edited, check configuration then update port

		global streamList

		#Get selected port
		rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
		rowpath = self.treeStore.get_path(rowiter)

		for s in streamList:
			for p in s.streamPorts:
				path = p.portInfo.portTreeRowRef.get_path()
				if path == rowpath:
					self.editing = p.portInfo.portName
					break

		if self.cb_check_input() == False:

			return

		self.editing = ""

		rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
		rowpath = self.treeStore.get_path(rowiter)


		for s in streamList:
			for p in xrange(0, len(s.streamPorts)):
				path = s.streamPorts[p].portInfo.portTreeRowRef.get_path()
				if path == rowpath:
					s.streamPorts[p].closePort()					
					s.streamPorts.pop(p)
					break

		self.treeStore.remove(rowiter)

		newPort = PortInfo()

		newPort.portName = self.addport.entry_name.get_text()
		newPort.portType = self.addport.combo_type.get_active_text()
		newPort.portStatus = "Stopped"
		newPort.portIO = self.addport.combo_rw.get_active_text()
		newPort.echo = self.addport.includeSelf.get_active()

		newPort.portLocation = self.addport.entry_port.get_text()
		newPort.portBaudRate = self.addport.entry_baud.get_text()
		newPort.portByteSize = self.addport.combo_bytesize.get_active_text()
		newPort.portParity = self.addport.combo_parity.get_active_text()
		newPort.portStopBits = self.addport.combo_stopbits.get_active_text()
		newPort.portXonXoff = self.addport.check_x.get_active()
		newPort.portRtsCts = self.addport.check_rtscts.get_active()
		newPort.portDsrdtr = self.addport.check_dsrdtr.get_active()
		
		newPort.netPort = self.addport.netPort.get_text()
		newPort.destIP = self.addport.destIP.get_text()
		newPort.destPort = self.addport.destPort.get_text()

		if self.addport.netTCP.get_active() == True:

			newPort.netUDP = False
			newPort.netTCP = True

		elif self.addport.netUDP.get_active() == True:

			newPort.netUDP = True
			newPort.netTCP = False
		
		if self.addport.netServer.get_active() == True:

			newPort.netServer = True
			newPort.netClient = False

		elif self.addport.netClient.get_active() == True:

			newPort.netServer = False
			newPort.netClient = True
		
		newPort.fileLocation = self.addport.FilePathEntry.get_text()

		if self.addport.fileAppend.get_active() == True:

			newPort.fileWA = "a"

		elif self.addport.fileOverwrite.get_active() == True:

			newPort.fileWA = "w"

		if self.addport.infilteron.get_active() == True:

			newPort.infilterUsed = True

			if self.addport.infilterBlacklist.get_active() == True:

				newPort.infilterBlacklist = True

			else:

				newPort.infilterWhitelist = True

			if self.addport.infilterStart.get_active() == True:

				newPort.infilterPosition = 1

			elif self.addport.infilterEnd.get_active() == True:

				newPort.infilterPosition = 2

			elif self.addport.infilterAnywhere.get_active() == True:

				newPort.infilterPosition = 3

			textbuffer = self.addport.infilterText.get_buffer()
			
			text = textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter())	
			newPort.infilterStrings = text.split(os.linesep)
			newPort.infilterStrings = filter(None, newPort.infilterStrings)

		if self.addport.outfilteron.get_active() == True:

			newPort.outfilterUsed = True

			if self.addport.outfilterBlacklist.get_active() == True:

				newPort.outfilterBlacklist = True

			else:

				newPort.outfilterWhitelist = True

			if self.addport.outfilterStart.get_active() == True:

				newPort.outfilterPosition = 1

			elif self.addport.outfilterEnd.get_active() == True:

				newPort.outfilterPosition = 2

			elif self.addport.outfilterAnywhere.get_active() == True:

				newPort.outfilterPosition = 3

			textbuffer = self.addport.outfilterText.get_buffer()
			
			text = textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter())	
			newPort.outfilterStrings = text.split(os.linesep)
			newPort.outfilterStrings = filter(None, newPort.outfilterStrings)

		sname = self.addport.combo_stream.get_active_text()

		port = Port()
		port.portInfo = newPort

		#Add the port to its stream
		for s in streamList:

			if s.streamName == sname:

				s.streamPorts.append(port)
				rowpath = s.streamTreeRowRef.get_path()
				rowiter = self.treeStore.append(self.treeStore.get_iter(rowpath), [newPort.portName, newPort.portStatus, newPort.portIO, newPort.portType])
				newPort.portTreeRowRef = gtk.TreeRowReference(self.treeStore, self.treeStore.get_path(rowiter))
				break

		self.addport.window.destroy()		
		saveSettings()

	def cb_check_input(self):
		#Checks port add/edit window for invalid input
		global streamList

		if len(self.addport.entry_name.get_text()) == 0:

                        md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please enter a port name")
			md.set_position(gtk.WIN_POS_CENTER)
			md.set_transient_for(self.addport.window)
			md.run()
			md.destroy()
			return False

		if self.editing != self.addport.entry_name.get_text():
			for s in streamList:
				for p in s.streamPorts:
				        if self.addport.entry_name.get_text() == p.portInfo.portName:

				                md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Port name already in use")
						md.set_position(gtk.WIN_POS_CENTER)
						md.set_transient_for(self.addport.window)
				                md.run()
				                md.destroy()
				                return False

		if self.addport.combo_stream.get_active_text() == None:

			md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select a stream")
			md.set_position(gtk.WIN_POS_CENTER)
			md.set_transient_for(self.addport.window)
                        md.run()
                        md.destroy()
                        return False

                if self.addport.combo_type.get_active_text() == None:

			md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select a port type")
			md.set_position(gtk.WIN_POS_CENTER)
			md.set_transient_for(self.addport.window)
                        md.run()
                        md.destroy()
                        return False

		if self.addport.combo_rw.get_active_text() == None:

			md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select input/output type")
			md.set_position(gtk.WIN_POS_CENTER)
			md.set_transient_for(self.addport.window)
                        md.run()
                        md.destroy()
                        return False

		if self.addport.combo_type.get_active_text() == "Network Port":
			
			for s in streamList:
				for p in s.streamPorts:
				        if self.addport.netPort.get_text() == p.portInfo.netPort:
						if self.addport.entry_name.get_text() != p.portInfo.portName:

						        md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Port already in use")
							md.set_position(gtk.WIN_POS_CENTER)
							md.set_transient_for(self.addport.window)
						        md.run()
						        md.destroy()
						        return False

			if self.addport.netTCP.get_active() == False and self.addport.netUDP.get_active() == False:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select network protocol")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			if len(self.addport.netPort.get_text()) == 0:
				
				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please enter host port number")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			if len(self.addport.destIP.get_text()) == 0:
				
				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please enter destination IP address")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			if len(self.addport.destPort.get_text()) == 0:
				
				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please enter destination port")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			try:

				if int(self.addport.netPort.get_text()) < 0 or int(self.addport.netPort.get_text()) > 65535:

					md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Port number must be between 0-65535")
					md.set_position(gtk.WIN_POS_CENTER)
					md.set_transient_for(self.addport.window)
				        md.run()
				        md.destroy()
				        return False

			except ValueError:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Port number must be a number between 0-65535")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
				md.run()
				md.destroy()
				return False

			md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Warning: You are about to set up a network port. Be aware that this data may be visible to other people, and could be altered for malicious purposes.")
			md.set_position(gtk.WIN_POS_CENTER)
			md.set_transient_for(self.addport.window)
			md.run()
			md.destroy()

		if self.addport.combo_type.get_active_text() == "File":

			if len(self.addport.FilePathEntry.get_text()) == 0:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select file location")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			for s in streamList:
				for p in s.streamPorts:
				        if self.addport.FilePathEntry.get_text() == p.portInfo.fileLocation:
						if self.addport.entry_name.get_text() != p.portInfo.portName:

						        md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "File already in use")
							md.set_position(gtk.WIN_POS_CENTER)
							md.set_transient_for(self.addport.window)
						        md.run()
						        md.destroy()
						        return False
		
		if self.addport.combo_type.get_active_text() == "Serial Port":

			if len(self.addport.entry_port.get_text()) == 0:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select port location")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			for s in streamList:
				for p in s.streamPorts:
				        if self.addport.entry_port.get_text() == p.portInfo.portLocation:
						if self.addport.entry_name.get_text() != p.portInfo.portName:

						        md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Port already in use")
							md.set_position(gtk.WIN_POS_CENTER)
							md.set_transient_for(self.addport.window)
						        md.run()
						        md.destroy()
						        return False

			if len(self.addport.entry_baud.get_text()) == 0:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select baud rate")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			try:
				int(self.addport.entry_baud.get_text())
			except:
				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Invalid Baud Rate")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False
				
			if self.addport.combo_bytesize.get_active_text() == None:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select bytesize")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			if self.addport.combo_parity.get_active_text() == None:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select parity")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

			if self.addport.combo_stopbits.get_active_text() == None:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Please select stopbits")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return False

		if self.addport.infilteron.get_active() == True:

			textbuffer = self.addport.infilterText.get_buffer()

			if textbuffer.get_char_count() == 0:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Filter Search Terms cannot be empty")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return

		if self.addport.outfilteron.get_active() == True:

			textbuffer = self.addport.outfilterText.get_buffer()

			if textbuffer.get_char_count() == 0:

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Filter Search Terms cannot be empty")
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.addport.window)
		                md.run()
		                md.destroy()
		                return

		return True

	def cb_but_remove(self, widget):
		#Remove button in configure window has been pressed

		global streamList

		#If nothing is selected, do nothing
		if self.tree.get_cursor()[0] == None:

			return

		else:
			string = ""
			if len(self.tree.get_cursor()[0]) == 1:
				#Get stream name
				rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
				rowpath = self.treeStore.get_path(rowiter)

				for s in streamList:
					path = s.streamTreeRowRef.get_path()
					if path == rowpath:
						string = s.streamName
						string += " and all its ports"
						break					
							
			else:
				#get port name

				rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
				rowpath = self.treeStore.get_path(rowiter)

				for s in streamList:
					for p in s.streamPorts:
						path = p.portInfo.portTreeRowRef.get_path()
						if path == rowpath:
							string = p.portInfo.portName
							break

			#prompt user to confirm they want to delete
			self.confirm = wn_confirm_delete(string)
			self.confirm.window.set_transient_for(self.window)
			self.confirm.but_acc.connect("clicked", self.cb_remove_but_acc)

	def cb_remove_but_acc(self, widget):

		global streamList

		if len(self.tree.get_cursor()[0]) == 1:
			#Delete stream and all associated ports

			rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
			rowpath = self.treeStore.get_path(rowiter)

			for s in xrange(0, len(streamList)):
				path = streamList[s].streamTreeRowRef.get_path()
				if path == rowpath:
					for p in streamList[s].streamPorts:
						p.closePort()
					streamList.pop(s)
					break

			self.treeStore.remove(rowiter)
		else:
			#Deletes just a port
			rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
			rowpath = self.treeStore.get_path(rowiter)

			for s in streamList:
				for p in xrange(0, len(s.streamPorts)):
					path = s.streamPorts[p].portInfo.portTreeRowRef.get_path()
					if path == rowpath:
						s.streamPorts[p].closePort()					
						s.streamPorts.pop(p)
						break

			self.treeStore.remove(rowiter)

		saveSettings()
		self.confirm.window.destroy()

	def cb_but_start_stop(self, widget):
		#Call back for start/stop button pressed
		
		if self.tree.get_cursor()[0] == None: #nothing selected

			return

		else:
			if len(self.tree.get_cursor()[0]) == 1: #Stream selected
				self.cb_start_stop_stream()
			else: #Port selected
				self.cb_start_stop_port()

	def cb_start_stop_stream(self):
		#Get stream selected

		global streamList

		rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
		rowpath = self.treeStore.get_path(rowiter)

		streamSelected = ""

		for s in streamList:
			path = s.streamTreeRowRef.get_path()
			if path == rowpath:
				streamSelected = s
				break

		if streamSelected.streamStatus == "Stopped":
			#Start Stream
			streamSelected.streamStatus = "Running"

			#update GUI
			self.treeStore.set_value(rowiter, 1, "Running")

		elif streamSelected.streamStatus == "Running":
			#Close Stream
			streamSelected.streamStatus = "Stopped"

			#update GUI
			self.treeStore.set_value(rowiter, 1, "Stopped")

	def cb_start_stop_port(self):
		#Start/stops currently selected port
		
		#Gets currently selected port
		rowiter = self.treeStore[self.tree.get_cursor()[0]].iter
		rowpath = self.treeStore.get_path(rowiter)

		stream = ""
		port = ""

		for s in streamList:
			for p in s.streamPorts:
				path = p.portInfo.portTreeRowRef.get_path()
				if path == rowpath:
					port = p
					stream = s
					break
		
		if port.portInfo.portStatus == "Stopped":
			#If port is stopped, open it
			status = port.openPort(s)

			if status == True:
				self.treeStore.set_value(rowiter, 1, "Running")
			else:
				#Unable to open port
				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Unable to open port: " + str(status))
				md.set_position(gtk.WIN_POS_CENTER)
				md.set_transient_for(self.window)
		                md.run()
		                md.destroy()

				port.closePort()

		elif port.portInfo.portStatus == "Running":
			#If port is running, close it
			port.closePort()
			self.treeStore.set_value(rowiter, 1, "Stopped")

	def cb_print(self, widget):
		#Debug function, prints out all stream and port configurations
		global streamList

		from pprint import pprint

		for s in streamList:

			print "STREAM:"

			pprint(vars(s))

			for p in s.streamPorts:

				print "PORT:"

				pprint(vars(s))

				print "PORT INFO\n"

				pprint(vars(p.portInfo))
		
class wn_confirm_delete():

	def __init__(self, string):

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_position(gtk.WIN_POS_CENTER)

		if os.environ.get('DESKTOP_SESSION') == 'ubuntu':

			self.window.set_size_request(450, 75)

		elif os.environ.get('DESKTOP_SESSION') == 'gnome':

			self.window.set_size_request(450, 85)

		else:

			self.window.set_size_request(450, 75)
		
		self.window.set_title("Confirm")
		self.window.set_border_width(8)
		self.window.set_resizable(False)
		self.window.set_modal(True)

		windowvbox = gtk.VBox(False, 0)

		inputhbox = gtk.HBox(False, 0)

		labelString = "Confirm you wish to remove " + string

		label = gtk.Label(labelString)

		inputhbox.pack_start(label, False, False,0)

		windowvbox.pack_start(inputhbox, False, False, 0)

		buttonhbox = gtk.HBox(False, 0)

		but_dec = gtk.Button("Cancel")
		but_dec.connect("clicked", self.cb_but_cancel)
		buttonhbox.pack_end(but_dec, False, False, 0)

		self.but_acc = gtk.Button("Accept")
		buttonhbox.pack_end(self.but_acc, False, False, 0)

		windowvbox.pack_end(buttonhbox, False, False, 0)

		self.window.add(windowvbox)
		self.window.show_all()

	def cb_but_cancel(self, i):

		self.window.destroy()

class wn_add_stream():

	def __init__(self):

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_position(gtk.WIN_POS_CENTER)

		if os.environ.get('DESKTOP_SESSION') == 'ubuntu':

			self.window.set_size_request(400, 75)

		elif os.environ.get('DESKTOP_SESSION') == 'gnome':

			self.window.set_size_request(400, 95)

		else:

			self.window.set_size_request(400, 75)

		self.window.set_title("New Stream")
		self.window.set_border_width(8)
		self.window.set_resizable(False)
		self.window.set_modal(True)

		windowvbox = gtk.VBox(False, 0)

		inputhbox = gtk.HBox(False, 0)

		label = gtk.Label("Enter Stream Name:")

		inputhbox.pack_start(label, False, False,0)

		self.nameEntry = gtk.Entry()
		self.nameEntry.set_activates_default(True)
		inputhbox.pack_start(self.nameEntry, True, True, 3)

		windowvbox.pack_start(inputhbox, False, False, 0)

		buttonhbox = gtk.HBox(False, 0)

		but_dec = gtk.Button("Cancel")
		but_dec.connect("clicked", self.cb_but_cancel)
		buttonhbox.pack_end(but_dec, False, False, 0)

		self.but_acc = gtk.Button("Accept")
		self.but_acc.set_flags(gtk.CAN_DEFAULT)
		buttonhbox.pack_end(self.but_acc, False, False, 0)

		windowvbox.pack_end(buttonhbox, False, False, 0)

		self.window.add(windowvbox)
		self.window.show_all()

	def cb_but_cancel(self, i):

		self.window.destroy()

class wn_port():
	#Creates the add/edit port window
	def __init__(self):

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_position(gtk.WIN_POS_CENTER)

		if os.environ.get('DESKTOP_SESSION') == 'ubuntu':

			self.window.set_size_request(395, 555)

		elif os.environ.get('DESKTOP_SESSION') == 'gnome':

			self.window.set_size_request(400, 605)

		else:

			self.window.set_size_request(365, 505)

		self.window.set_title("Add Ports")
		self.window.set_border_width(8)
		self.window.set_resizable(False)
		self.window.set_modal(True)

		windowvbox = gtk.VBox(False, 0)

		nb = gtk.Notebook()
		nb.set_tab_pos(gtk.POS_TOP)
		nb.set_show_border = True
		nb.set_show_tabs = True

		frame = gtk.Frame("Port Settings")
		frame.set_border_width(8)
		
		#Each OS has different sized widgets, so different sized windows must be used to accomodate them
		if os.environ.get('DESKTOP_SESSION') == 'ubuntu':
			#Ubuntu
			frame.set_size_request(350, 477)

		elif os.environ.get('DESKTOP_SESSION') == 'gnome':
			#Gnome
			frame.set_size_request(350, 517)

		else:
			#Windows
			frame.set_size_request(350, 427)
		

		fvbox = gtk.VBox(False, 0)

		fhbox = gtk.HBox(False, 0)

		label = gtk.Label("Port Name")
		fhbox.pack_start(label, False, False, 3)

		self.entry_name = gtk.Entry()
		fhbox.pack_start(self.entry_name, True, True, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		label = gtk.Label("Stream")
		fhbox.pack_start(label, False, False, 3)

		self.combo_stream = gtk.combo_box_new_text()
		
		for s in streamList:
			self.combo_stream.append_text(s.streamName)

		fhbox.pack_start(self.combo_stream, True, True, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		label = gtk.Label("Type")
		fhbox.pack_start(label, False, False, 3)

		self.combo_type = gtk.combo_box_new_text()
		self.combo_type.append_text("Serial Port")
		self.combo_type.append_text("Network Port")
		self.combo_type.append_text("File")
		self.combo_type.connect("changed", self.typechange)
		fhbox.pack_start(self.combo_type, True, True, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		label = gtk.Label("Input/Output")
		fhbox.pack_start(label, False, False, 3)

		self.combo_rw = gtk.combo_box_new_text()
		self.combo_rw.append_text("Input")
		self.combo_rw.append_text("Output")
		self.combo_rw.append_text("Input and Output")
		self.combo_rw.connect("changed", self.cb_rw_change)
		fhbox.pack_start(self.combo_rw, True, True, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.includeSelf = gtk.CheckButton("Echo incoming data back out on this port")
		self.includeSelf.set_sensitive(False)
		fhbox.pack_start(self.includeSelf, False, False, 3)		

		fvbox.pack_start(fhbox, False, False, 3)

		iframe = gtk.Frame()		
		iframe.set_border_width(8)
		if os.environ.get('DESKTOP_SESSION') == 'ubuntu':

			iframe.set_size_request(100, 298)

		elif os.environ.get('DESKTOP_SESSION') == 'gnome':

			iframe.set_size_request(100, 286)

		else:

			iframe.set_size_request(100, 271)
		
		iframebox = gtk.VBox(False, 0)

		self.ivbox1 = gtk.VBox(False, 0)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Port Location")
		ihbox.pack_start(label, False, False, 3)

		self.entry_port = gtk.Entry()
		ihbox.pack_start(self.entry_port, True, True, 3)

		self.ivbox1.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Baud Rate")
		ihbox.pack_start(label, False, False, 3)

		self.entry_baud = gtk.Entry()
		ihbox.pack_start(self.entry_baud, True, True, 3)

		self.ivbox1.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Bytesize")
		ihbox.pack_start(label, False, False, 3)

		self.combo_bytesize = gtk.combo_box_new_text()
		self.combo_bytesize.append_text("5")
		self.combo_bytesize.append_text("6")
		self.combo_bytesize.append_text("7")
		self.combo_bytesize.append_text("8")
		ihbox.pack_start(self.combo_bytesize, True, True, 3)

		self.ivbox1.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Parity")
		ihbox.pack_start(label, False, False, 3)

		self.combo_parity = gtk.combo_box_new_text()
		self.combo_parity.append_text("None")
		self.combo_parity.append_text("Even")
		self.combo_parity.append_text("Odd")
		self.combo_parity.append_text("Mark")
		self.combo_parity.append_text("Space")
		ihbox.pack_start(self.combo_parity, True, True, 3)

		self.ivbox1.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Stopbits")
		ihbox.pack_start(label, False, False, 3)

		self.combo_stopbits = gtk.combo_box_new_text()
		self.combo_stopbits.append_text("1")
		self.combo_stopbits.append_text("1.5")
		self.combo_stopbits.append_text("2")
		ihbox.pack_start(self.combo_stopbits, True, True, 3)

		self.ivbox1.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)

		self.check_x = gtk.CheckButton("XON/XOFF", False)
		ihbox.pack_start(self.check_x, True, True, 3)

		self.check_rtscts = gtk.CheckButton("RTS/CTS", False)
		ihbox.pack_start(self.check_rtscts, True, True, 3)

		self.check_dsrdtr = gtk.CheckButton("DSR/DTR", False)
		ihbox.pack_start(self.check_dsrdtr, True, True, 3)

		self.ivbox1.pack_start(ihbox, False, False, 3)
		
		self.ivbox2 = gtk.VBox(False, 0)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Protocol: ")
		ihbox.pack_start(label, False, False, 3)

		self.netTCP = gtk.RadioButton(None, "TCP")
		self.netTCP.set_active(True)
		self.netTCP.connect('toggled', self.cb_tcp_udp)
		ihbox.pack_start(self.netTCP, True, True, 3)

		self.netUDP = gtk.RadioButton(self.netTCP, "UDP")
		self.netUDP.connect('toggled', self.cb_tcp_udp)
		ihbox.pack_start(self.netUDP, True, True, 3)

		self.ivbox2.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Act as: ")
		ihbox.pack_start(label, False, False, 3)

		self.netServer = gtk.RadioButton(None, "Server")
		self.netServer.set_active(True)
		ihbox.pack_start(self.netServer, True, True, 3)

		self.netClient = gtk.RadioButton(self.netServer, "Client")
		ihbox.pack_start(self.netClient, True, True, 3)

		self.ivbox2.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Use Port Number:")
		ihbox.pack_start(label, False, False, 3)

		self.netPort = gtk.Entry()
		ihbox.pack_start(self.netPort, True, True, 3)

		self.ivbox2.pack_start(ihbox, False, False, 3)
		
		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Connection IP:")
		ihbox.pack_start(label, False, False, 3)

		self.destIP = gtk.Entry()
		ihbox.pack_start(self.destIP, True, True, 3)

		self.ivbox2.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("Connection Port:")
		ihbox.pack_start(label, False, False, 3)

		self.destPort = gtk.Entry()
		ihbox.pack_start(self.destPort, True, True, 3)

		self.ivbox2.pack_start(ihbox, False, False, 3)
		
		self.ivbox3 = gtk.VBox(False, 0)

		ihbox = gtk.HBox(False, 0)

		label = gtk.Label("File Location")
		ihbox.pack_start(label, False, False, 3)
		
		self.FilePathEntry = gtk.Entry()
		ihbox.pack_start(self.FilePathEntry, True, True, 3)
		
		but_FP = gtk.Button("Select")
		but_FP.connect("clicked", self.cb_but_change_path)
		ihbox.pack_end(but_FP, False, False, 0)

		self.ivbox3.pack_start(ihbox, False, False, 3)

		ihbox = gtk.HBox(False, 0)
		
		self.fileAppend = gtk.RadioButton(None, "Append existing file")
		self.fileAppend.set_active(True)
		ihbox.pack_start(self.fileAppend, True, True, 3)

		self.fileOverwrite = gtk.RadioButton(self.fileAppend, "Overwrite existing file")
		ihbox.pack_start(self.fileOverwrite, True, True, 3)

		self.ivbox3.pack_start(ihbox, False, False, 3)
		
		iframebox.pack_start(self.ivbox1, False, False, 3)
		iframebox.pack_start(self.ivbox2, False, False, 3)
		iframebox.pack_start(self.ivbox3, False, False, 3)
		
		iframe.add(iframebox)

		fvbox.pack_start(iframe, False, False, 3)

		frame.add(fvbox)

		label = gtk.Label("Settings")

		nb.append_page(frame, label)

		filter_frame = gtk.Frame("Filter")		
		filter_frame.set_border_width(8)
		filter_frame.set_size_request(100, 321)

		fvbox = gtk.VBox(False, 0)

		fhbox = gtk.HBox(False, 0)

		self.infilteron = gtk.CheckButton("Filter incoming data on this port")
		self.inHandler = self.infilteron.connect("toggled", self.cb_infilt_change)
		fhbox.pack_start(self.infilteron, False, False, 3)		

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.infilterWhitelist = gtk.RadioButton(None, "Whitelist Filter")
		self.infilterWhitelist.set_sensitive(False)
		fhbox.pack_start(self.infilterWhitelist, False, False, 3)

		self.infilterBlacklist = gtk.RadioButton(self.infilterWhitelist, "Blacklist Filter")
		self.infilterBlacklist.set_sensitive(False)
		fhbox.pack_start(self.infilterBlacklist, False, False, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.searchLabel = gtk.Label("Search for string at the:")		
		self.searchLabel.set_sensitive(False)
		fhbox.pack_start(self.searchLabel, False, False, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.infilterStart = gtk.RadioButton(None, "Start")
		self.infilterStart.set_sensitive(False)
		fhbox.pack_start(self.infilterStart, False, False, 3)

		self.infilterEnd = gtk.RadioButton(self.infilterStart, "End")		
		self.infilterEnd.set_sensitive(False)
		fhbox.pack_start(self.infilterEnd, False, False, 3)

		self.infilterAnywhere = gtk.RadioButton(self.infilterStart, "Anywhere")		
		self.infilterAnywhere.set_sensitive(False)
		fhbox.pack_start(self.infilterAnywhere, False, False, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.entryLabel = gtk.Label("Enter each string to be filtered on a new line:")
		self.entryLabel.set_sensitive(False)
		fhbox.pack_start(self.entryLabel, False, False, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		self.scrolledWindow = gtk.ScrolledWindow()
		self.scrolledWindow.set_sensitive(False)
		self.scrolledWindow.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		self.scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		self.infilterText = gtk.TextView()

		self.scrolledWindow.add(self.infilterText)

		fvbox.pack_start(self.scrolledWindow)

		fhbox = gtk.HBox(False, 0)

		self.outfilteron = gtk.CheckButton("Filter outgoing data on this port")
		self.outHandler = self.outfilteron.connect("toggled", self.cb_outfilt_change)
		fhbox.pack_start(self.outfilteron, False, False, 3)		

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.outfilterWhitelist = gtk.RadioButton(None, "Whitelist Filter")
		self.outfilterWhitelist.set_sensitive(False)
		fhbox.pack_start(self.outfilterWhitelist, False, False, 3)

		self.outfilterBlacklist = gtk.RadioButton(self.outfilterWhitelist, "Blacklist Filter")
		self.outfilterBlacklist.set_sensitive(False)
		fhbox.pack_start(self.outfilterBlacklist, False, False, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.outsearchLabel = gtk.Label("Search for string at the:")		
		self.outsearchLabel.set_sensitive(False)
		fhbox.pack_start(self.outsearchLabel, False, False, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.outfilterStart = gtk.RadioButton(None, "Start")
		self.outfilterStart.set_sensitive(False)
		fhbox.pack_start(self.outfilterStart, False, False, 3)

		self.outfilterEnd = gtk.RadioButton(self.outfilterStart, "End")		
		self.outfilterEnd.set_sensitive(False)
		fhbox.pack_start(self.outfilterEnd, False, False, 3)

		self.outfilterAnywhere = gtk.RadioButton(self.outfilterStart, "Anywhere")		
		self.outfilterAnywhere.set_sensitive(False)
		fhbox.pack_start(self.outfilterAnywhere, False, False, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		fhbox = gtk.HBox(False, 0)

		self.outentryLabel = gtk.Label("Enter each string to be filtered on a new line:")
		self.outentryLabel.set_sensitive(False)
		fhbox.pack_start(self.outentryLabel, False, False, 3)

		fvbox.pack_start(fhbox, False, False, 3)

		self.outscrolledWindow = gtk.ScrolledWindow()
		self.outscrolledWindow.set_sensitive(False)
		self.outscrolledWindow.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		self.outscrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		self.outfilterText = gtk.TextView()

		self.outscrolledWindow.add(self.outfilterText)

		fvbox.pack_start(self.outscrolledWindow)

		filter_frame.add(fvbox)

		nb.append_page(filter_frame, gtk.Label("Filter Settings"))

		windowvbox.pack_start(nb, False, False, 0)

		buttonhbox = gtk.HBox(False, 0)

		but_dec = gtk.Button("Cancel")
		but_dec.connect("clicked", self.cb_but_cancel)
		buttonhbox.pack_end(but_dec, False, False, 0)

		self.but_acc = gtk.Button("Accept")
		buttonhbox.pack_end(self.but_acc, False, False, 0)

		windowvbox.pack_end(buttonhbox, False, False, 0)

		self.window.add(windowvbox)
		self.window.show_all()
		self.ivbox1.hide_all()
		self.ivbox2.hide_all()
		self.ivbox3.hide_all()

	def cb_rw_change(self, widget):
		#Read/write has changed, let filters know
		#so that they can prevent unusable filters being setup

		if self.combo_rw.get_active_text() == "Input":

			self.outfilteron.set_active(False)
			
		elif self.combo_rw.get_active_text() == "Output":

			self.infilteron.set_active(False)

		if self.combo_rw.get_active_text() == "Input and Output":

			self.includeSelf.set_sensitive(True)
		else:
			self.includeSelf.set_sensitive(False)

	def cb_tcp_udp(self, widget):
		#User has changed protocol, update GUI

		if self.netTCP.get_active() == True:
			self.netServer.set_sensitive(True)
			self.netClient.set_sensitive(True)
		else:
			self.netServer.set_sensitive(False)
			self.netClient.set_sensitive(False)

	def cb_infilt_change(self, widget):
		#Change in in filter's status

		if widget.get_active() == True:

			if self.combo_rw.get_active_text() == "Input" or self.combo_rw.get_active_text() == "Input and Output":

				self.infilterWhitelist.set_sensitive(True)
				self.infilterBlacklist.set_sensitive(True)
				self.searchLabel.set_sensitive(True)
				self.infilterStart.set_sensitive(True)
				self.infilterEnd.set_sensitive(True)
				self.infilterAnywhere.set_sensitive(True)
				self.entryLabel.set_sensitive(True)
				self.scrolledWindow.set_sensitive(True)

			else:

				#changes the widget back to original state, and blocks recursive calls
				widget.handler_block(self.inHandler)
				widget.set_active(False)
				widget.handler_unblock(self.inHandler)

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Port is not currently configured to receive data")
				md.set_position(gtk.WIN_POS_CENTER)
				md.run()
				md.destroy()

		else:

			self.infilterWhitelist.set_sensitive(False)
			self.infilterBlacklist.set_sensitive(False)
			self.searchLabel.set_sensitive(False)
			self.infilterStart.set_sensitive(False)
			self.infilterEnd.set_sensitive(False)
			self.infilterAnywhere.set_sensitive(False)
			self.entryLabel.set_sensitive(False)
			self.scrolledWindow.set_sensitive(False)

		
	def cb_outfilt_change(self, widget):
		#Change in outfilter's status

		if widget.get_active() == True:

			if self.combo_rw.get_active_text() == "Output" or self.combo_rw.get_active_text() == "Input and Output":

				self.outfilterWhitelist.set_sensitive(True)
				self.outfilterBlacklist.set_sensitive(True)
				self.outsearchLabel.set_sensitive(True)
				self.outfilterStart.set_sensitive(True)
				self.outfilterEnd.set_sensitive(True)
				self.outfilterAnywhere.set_sensitive(True)
				self.outentryLabel.set_sensitive(True)
				self.outscrolledWindow.set_sensitive(True)

			else:

				#changes the widget back to original state, and blocks recursive calls
				widget.handler_block(self.outHandler)
				widget.set_active(False)
				widget.handler_unblock(self.outHandler)

				md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Port is not currently configured to output data")
				md.set_position(gtk.WIN_POS_CENTER)
				md.run()
				md.destroy()

		else:

			self.outfilterWhitelist.set_sensitive(False)
			self.outfilterBlacklist.set_sensitive(False)
			self.outsearchLabel.set_sensitive(False)
			self.outfilterStart.set_sensitive(False)
			self.outfilterEnd.set_sensitive(False)
			self.outfilterAnywhere.set_sensitive(False)
			self.outentryLabel.set_sensitive(False)
			self.outscrolledWindow.set_sensitive(False)

		
	def cb_but_change_path(self, widget):
	
		dialog = gtk.FileChooserDialog("Save File Location", None, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		
		filter = gtk.FileFilter()
		filter.set_name("All files")
		filter.add_pattern("*")
		dialog.add_filter(filter)
				
		response = dialog.run()
		if response == gtk.RESPONSE_OK:
			self.FilePathEntry.set_text(dialog.get_filename())
		dialog.destroy()
		
	def typechange(self, widget):
	
		self.combo_rw.remove_text(0)
		self.combo_rw.remove_text(0)
		self.combo_rw.remove_text(0)

		if widget.get_active_text() == 'Serial Port':

			self.ivbox1.show_all()
			self.ivbox2.hide_all()
			self.ivbox3.hide_all()
			
			self.combo_rw.append_text("Input")
			self.combo_rw.append_text("Output")
			self.combo_rw.append_text("Input and Output")

		elif widget.get_active_text() == 'Network Port':

			self.ivbox1.hide_all()
			self.ivbox2.show_all()
			self.ivbox3.hide_all()
			
			self.combo_rw.append_text("Input")
			self.combo_rw.append_text("Output")
			self.combo_rw.append_text("Input and Output")

		elif widget.get_active_text() == 'File':

			self.ivbox1.hide_all()
			self.ivbox2.hide_all()
			self.ivbox3.show_all()

			self.combo_rw.append_text("Output")

	def cb_but_cancel(self, widget):

		self.window.destroy()

def saveSettings():
	#Saves current stream and port information to disk, for persistence between sessions

	global streamList

	try:
		f = open(".portSettings", "w")

		#Test to check file reading when loaded
		t = "Pickle Test"
		pickle.dump(t, f)

		pickle.dump(len(streamList), f)

		for s in streamList:
			
			pickle.dump(s.streamName, f)
			pickle.dump(len(s.streamPorts), f)

			for p in s.streamPorts:

				#Tree Row Iters cannot be pickled as they are memory location based
				#Therefore they are blanked, then saved, then set back to their original value
				temp = copy.copy(p.portInfo)
				temp.portStatus = "Stopped"
				temp.portTreeRowRef = None
				pickle.dump(temp, f)
	
		f.close()
	
	except:
		import sys
		print sys.exc_info()
		md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Unable to access configuration file. Changes can't be saved.")
		md.set_position(gtk.WIN_POS_CENTER)
		md.run()
		md.destroy()
	

def loadSettings():
	#Checks if a configuration file exits, and if so reads it in

	global streamList

	try:
		f = open(".portSettings", "r")

		t = pickle.load(f)
		if t == "Pickle Test":
			streamList = []

			for s in xrange(0, pickle.load(f)):

				ns = Stream()
				ns.streamName = pickle.load(f)

				for p in xrange(0, pickle.load(f)):

					np = Port()
					np.portInfo = pickle.load(f)

					ns.streamPorts.append(np)

				streamList.append(ns)
	
		f.close()

	except:
		pass

if __name__ == "__main__":

	loadSettings() #Loads settings from previous sessions
	systemTray = wn_system_tray() #Attempts to create system tray icon

	if systemTray.tray != None:
		gtk.main()

