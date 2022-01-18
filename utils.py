# -*- coding: utf-8 -*-

# This file contains some general purpose functions used in most examples.
# By moving it here in only one place, it is easier to maintain and any change
# becomes available for all examples.
# The code in each example is also simpler and easier to read and understand.

import os
import time
import FUSTHON


def initLog(fus, name):
	"""Initializes the logging system and use a file with given name as output."""
	fus.setLogFile (name)          # create a log file named "<name>-<datetime>.log"
	fus.enableLogStderr (False)    # disable output to console
	fus.setLogLevel (FUSTHON.LogLevel.VERBOSE)  # set max details


def connect(fus):
	"""Attempts a connection to the generator."""
	
	# Loads the generator description file if found (optional).
	# This is required to compute ShotResult powers and convert channel raw values into physical units.
	generatorFile = "generator.ini"
	if "IGTFUS_TEST_GENCONF" in os.environ:
		generatorFile = os.environ["IGTFUS_TEST_GENCONF"]
	if os.path.exists (generatorFile):
		fus.gen.loadDefinition (generatorFile)
		generatorAddress = fus.getDefinitionHost()
		generatorPort = fus.getDefinitionPort()
	else: # you have to provide the connection info
		generatorAddress = "127.0.0.1"
		generatorPort = 1670
		try:
			if "IGTFUS_TEST_PORT" in os.environ:
				generatorPort = int(os.environ["IGTFUS_TEST_PORT"])
		except:
			generatorPort = 1670

	# Attempt a connection to the generator, wait 4s max.
	print ("Trying to connect to %s on port %d:" % (generatorAddress, generatorPort))
	if fus.connect (generatorAddress, generatorPort, 4000):
		print ("Ok")
	else:
		print ("Failure")
		exit (1)


class ExecListener(FUSTHON.FUSListener):
	"""
	A listener class used to illustrate how to receive events sent by the FUS object,
	and also how to wait for the end of an execution properly.
	"""

	def __init__(self):
		FUSTHON.FUSListener.__init__(self)
		self.m_running = False
		self.shotResults = []
		self.execResult = None

	def onConnect(self):
		print ("Listener: CONNECTED")

	def onDisconnect(self, reason):
		self.m_running = False
		print ("Listener: DISCONNECTED (reason=%d)" % reason)

	def onExecStart (self, execID, execCount, execFlags, elecMode, trigMode, mechMode):
		self.m_running = True
		self.shotResults = []
		print ("Listener: EXEC START (count=%d, elecMode=%d, trigMode=%d)" % (execCount, elecMode, trigMode))

	def onShotResult (self, execID, shot_result):
		self.shotResults.append(shot_result)
		print ("Listener: SHOT RESULT (exec#%d, shot#%d, dur(us)=%d)" % (
			shot_result.execIndex(), shot_result.index(), shot_result.duration()))

	def onExecResult (self, exec_result):
		if exec_result.isFinished():
			self.execResult = exec_result
			self.m_running = False
		print ("Listener: EXEC RESULT (exec#%d, remain=%d)" % (exec_result.index(), exec_result.remaining()))


	def waitExecution(self):
		# Start with a sleep to make sure the start event has been received
		# and m_running has been set to true.
		while True:
			time.sleep(0.2)
			if not self.m_running:
				return
	
	def printExecResult(self):
		msg = "Execution result: "
		if self.execResult is None:
			msg += "Nothing received"
		elif self.execResult.isError():
			msg += "ERROR\n"
			msg += "  code: %d / %s\n" % (self.execResult.status(), self.execResult.statusName())
			msg += "  message: " + self.execResult.errorMessage()
		else:
			msg += "SUCCESS"
		print (msg)
