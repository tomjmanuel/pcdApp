#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Shows how to open a connection to the generator and read its configuration.
#

import os
import FUSTHON
import utils

# The module version
print ("Module version: "+FUSTHON.buildVersion())
print ("Build date    : "+FUSTHON.buildDate())

# the main FUS object
fus = FUSTHON.FUS()
# utils.initLog(fus, "config")  # uncomment to enable logging in file

# Opens the connection to the generator (see utils.py for details)
utils.connect(fus)

try:
	# ----- Global configuration
	print("Internal configuration:")
	TYPES = (FUSTHON.BoardType.PROCESSOR, FUSTHON.BoardType.SYNTHESIZER, FUSTHON.BoardType.AMPLIFIER, FUSTHON.BoardType.MECHANICS)
	for btype in TYPES:
		nboards = fus.getBoardCount(btype)
		print ("- %-11s boards : %d" % (str(btype), nboards))
		if nboards > 0:
			vHW = fus.getHardwareVersion (btype)
			vSW = fus.getFirmwareVersion (btype)
			print ("  Versions: hardware=%s / firmware=%s" % (vHW, vSW))
	print ("")

	# ----- Generator configuration
	# Number of channels/outputs on the generator
	print ("Channel count: %d" % fus.gen.getChannelCount())
	
	# Maximum number of shots in one trajectory
	print ("Trajectory max size:")
	print ("- NORMAL: %d" % fus.gen.getMaxTrajectorySize(FUSTHON.ElecExecMode.NORMAL))
	print ("- REPEAT: %d" % fus.gen.getMaxTrajectorySize(FUSTHON.ElecExecMode.REPEAT))
	
	# Number of trajectory buffers on the generator
	print ("Buffer count: %d" % fus.gen.getBufferCount())
	
	# Number of measurements per channel on amplifier boards
	print ("Channel measurement count: %d" % fus.gen.getChannelMeasureCount())
	
	# Number of current measures on amplifier boards (total, not per board)
	print ("Amplifier currents: %d" % fus.gen.getAmplifierCurrentCount())
	
	# Number of current temperature sensors on the amplifier boards (total)
	print ("Amplifier temperatures: %d" % fus.gen.getAmplifierTemperatureCount())
	
	# Number of power supplies monitored (voltage)
	print ("Power supplies: %d" % fus.gen.getPowerSupplyCount())
	
	# Tells if this generator can handle external signals to trigger shots
	print ("Has trigger input: " + str(fus.gen.hasTriggerInput()))
	
	# Tells if this generator can handle ramps (at beginning and end) of shots
	print ("Has shot ramp: " + str(fus.gen.hasShotRamp()))
	print ("")
	
	# All timings are in microseconds
	print ("Shot timing constraints: [min, max] duration / [min, max] total")
	print ("- NORMAL: [%d, %d] / [%d, %d] us" % (fus.gen.getMinShootingDuration(), fus.gen.getMaxShootingDuration(), fus.gen.getMinTotalShotDuration(), fus.gen.getMaxTotalShotDuration()))
	print ("- NORMAL (no result): [%d, %d] / [%d, %d] us" % (fus.gen.getMinShootingDuration(), fus.gen.getMaxShootingDuration(), fus.gen.getMinTotalShotDuration(FUSTHON.ElecExecMode.NORMAL, FUSTHON.ExecFlag.OMIT_ALL_MEASURES), fus.gen.getMaxTotalShotDuration()))
	print ("- REPEAT: [%d, %d] / [%d, %d] us" % (fus.gen.getMinShootingDuration(FUSTHON.ElecExecMode.REPEAT), fus.gen.getMaxShootingDuration(FUSTHON.ElecExecMode.REPEAT), fus.gen.getMinTotalShotDuration(FUSTHON.ElecExecMode.REPEAT), fus.gen.getMaxTotalShotDuration(FUSTHON.ElecExecMode.REPEAT)))
	print ("")
	
	# Minimum delay between trajectory executions (when repeating trajectories)
	print ("Min trajectory delay: %d us" % fus.gen.getMinTrajectoryDelay())
	# Maximum delay between trajectory executions (when repeating trajectories)
	print ("Max trajectory delay: %d us" % fus.gen.getMaxTrajectoryDelay())
	# Maximum ramp duration (at beginning and end) of a shot
	print ("Max ramp duration: %d us" % fus.gen.getMaxRampDuration())
	print ("")

	# Thresholds
	print ("Amplitude threshold: %d" % fus.gen.readAmplitudeThreshold())
	print ("Output current threshold: %d" % fus.gen.readOutCurrentThreshold())

	# Peripheral state
	print ("Amplifier power supply enabled: "+str(fus.readPeripheralState(FUSTHON.Peripheral.POWER_SUPPLY_28V)))
	print ("Slave boards active: "+str(fus.readPeripheralState(FUSTHON.Peripheral.SLAVE_BOARDS)))
	print ("")

	# Board infos (for AMPLIFIER boards)
	print ("Amplifier boards infos:")
	for i in range(fus.getBoardCount(FUSTHON.BoardType.AMPLIFIER)):
		info = fus.readBoardInfo (FUSTHON.BoardType.AMPLIFIER, i)
		print ("  amplifier #%2d: CRC=0x%04X, size=%d, date=%s" % (i, info.firmwareCRC(), info.firmwareSize(), info.firmwareDatetime()))

except Exception as why:
	print ("Exception: "+str(why))

print ("Disconnecting")
fus.disconnect()
