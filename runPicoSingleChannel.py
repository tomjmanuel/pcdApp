# -*- coding: utf-8 -*-
"""
Created on Thu Dec 17 13:20:17 2020

Setup the picoscope in the IGT cabinet to collect on 1 channels given a trigger

@author: tom
"""

import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc

class runPico:
	
	def __init__(self, postTriggerSamples, timebase, vRange):
		
		self.postTriggerSamples = ctypes.c_int16(postTriggerSamples)
		self.PTSint = postTriggerSamples
		self.PTSlong = ctypes.c_int32(postTriggerSamples)
		self.timebase = timebase
		self.vRange = vRange # "PS5000A_10MV", "PS5000A_50MV",20,100,200,500
		
		# Create chandle and self.status ready for use
		self.chandle = ctypes.c_int16()
		self.status = {}
		
		# Open 5000 series PicoScope
		resolution =ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"]
		self.status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(self.chandle), None, resolution)
		self.dataA = []
		self.time = []
		self.connectedFlag = 0 # track connectivity

		try:
			assert_pico_ok(self.status["openunit"])
			self.connectedFlag=1
		except:  # PicoNotOkError:

			powerStatus = self.status["openunit"]

			if powerStatus == 286:
				self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
			elif powerStatus == 282:
				self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
			else:
				raise

			assert_pico_ok(self.status["changePowerSource"])
		
		# Set up Channel Variables
		enabled = 1

		analogue_offset = 0.0
		coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
		
		# Set up channel A
		channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
		chARange = ps.PS5000A_RANGE[self.vRange]
		self.status["setChA"] = ps.ps5000aSetChannel(self.chandle, channel, enabled, coupling_type, chARange, analogue_offset)
		assert_pico_ok(self.status["setChA"])
		
		# find maximum ADC count value
		# handle = chandle
		# pointer to value = ctypes.byref(self.maxADC)
		self.maxADC = ctypes.c_int16()
		self.status["maximumValue"] = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(self.maxADC))
		assert_pico_ok(self.status["maximumValue"])

		# segment index = 0
		self.timeIntervalns = ctypes.c_float()
		#self.postTriggerSamples = ctypes.c_int32()
		self.status["getTimebase2"] = ps.ps5000aGetTimebase2(self.chandle, self.timebase, self.PTSlong, ctypes.byref(self.timeIntervalns), ctypes.byref(self.postTriggerSamples), 0)
		assert_pico_ok(self.status["getTimebase2"])

		# Set up single trigger
		enabled = 1
		source = ps.PS5000A_CHANNEL["PS5000A_EXTERNAL"]
		trigRange = ps.PS5000A_RANGE['PS5000A_500MV']
		threshold = int(mV2adc(20,trigRange, self.maxADC))
		direction = 2 # PS5000A_RISING
		delay = 60 # us
		delaySamp = int(delay*1E-3 / self.timeIntervalns.value)
		autoTrigger = 0 # set to 0, makes picoscope wait indefinitely for a rising edge
		self.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.chandle, enabled, source, threshold, direction, delaySamp, autoTrigger)
		assert_pico_ok(self.status["trigger"])
		
	def runBlock(self):
		self.status["runBlock"] = ps.ps5000aRunBlock(self.chandle, 0, self.PTSint, self.timebase, None, 0, None, None)
		assert_pico_ok(self.status["runBlock"])
		#print("here")

	def waitForFinish(self):
		# Check for data collection to finish using ps5000aIsReady
		#print("here wait")
		ready = ctypes.c_int16(0)
		check = ctypes.c_int16(0)
		while ready.value == check.value:
			self.status["isReady"] = ps.ps5000aIsReady(self.chandle, ctypes.byref(ready))
		
		bufferAMax = (ctypes.c_int16 * self.PTSint)()
		bufferAMin = (ctypes.c_int16 * self.PTSint)() # used for downsampling which isn't in the scope of this example
	
		
		############ CHANNEL A ###########
		#print("hereb")
		# Set data buffer location for data collection from channel A
		# handle = self.chandle
		source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
		# pointer to buffer max = ctypes.byref(bufferAMax)
		# pointer to buffer min = ctypes.byref(bufferAMin)
		# buffer length = self.postTriggerSamples
		# segment index = 0
		# ratio mode = PS5000A_RATIO_MODE_NONE = 0
		self.status["setDataBuffersA"] = ps.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), self.PTSint, 0, 0)
		assert_pico_ok(self.status["setDataBuffersA"])
		
		
		# create overflow loaction
		overflow = ctypes.c_int16()
		# create converted type self.postTriggerSamples
		cmaxSamples = self.PTSlong
		
		# Retried data from scope to buffers assigned above
		# handle = self.chandle
		# start index = 0
		# pointer to number of samples = ctypes.byref(cself.postTriggerSamples)
		# downsample ratio = 0
		# downsample ratio mode = PS5000A_RATIO_MODE_NONE
		# pointer to overflow = ctypes.byref(overflow))
		self.status["getValues"] = ps.ps5000aGetValues(self.chandle, 0, ctypes.byref(cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
		assert_pico_ok(self.status["getValues"])
		
		# convert ADC counts data to mV
		chARange = ps.PS5000A_RANGE[self.vRange]
		adc2mVChAMax =  adc2mV(bufferAMax, chARange, self.maxADC)
		
		# Create time data
		#print("here 2")
		time = np.linspace(0, (cmaxSamples.value) * self.timeIntervalns.value, cmaxSamples.value)
		self.time = time

		
		# add data to self.data
		self.dataA.append(adc2mVChAMax[:])
		
	def getDataA(self):
		return self.dataA
	
	def getTime(self):
		return self.time
	
	def clearData(self):
		self.dataA = []

	def checkConnected(self):
		return self.connectedFlag

	def disconnect(self):
		self.status["close"] = ps.ps5000aCloseUnit(self.chandle)

		
	



