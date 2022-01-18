#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Shows how to create, send and execute a simple electronic trajectory
# in NORMAL mode, and how to read its ShotResults.
# nav cwd to Tom/IGTFUS_SDK/python/examples
#

import os
import FUSTHON
import utils
import numpy as np
import transducerXYZ
fus = FUSTHON.FUS()
# utils.initLog(fus, "execRepeat")  # uncomment to enable logging in file

listener = utils.ExecListener()
fus.registerListener (listener)

# Opens the connection to the generator (see utils.py for details)
utils.connect(fus)

try:
	# Create the trajectory and add all its shots.
	channels = fus.gen.getChannelCount()
	traj = FUSTHON.ElectronicTrajectory(channels)
	execMode = FUSTHON.ElecExecMode.REPEAT
	
	# in repeat mode, here are time constraints
	# MinTotalShotDuration: 800 us (PRF =1250 Hz )
	# MinShootingDuration: 0 us (there is not min)
	# MaxTotalShotDUration: 15,000,000 us (15 s)
	# MaxShootingDuration:  2,000,000 us (actual sound on)
	
	# there is no min ramp duration
	# max ramp duration found with getMaxRampDuration
	
	# not documented but observed, offTime seems to be limited to values >400 (turns into cw at <400)
	
	# custom variable
	ampperc = 8		# amp percent
	relRamp = 1	# ramp up time (us)
	onTime = 40	# on time of pulse
	offTime = 200000	# off time before next pulse (around 500 ms for beammaps)
	execCount = 2000   # how many times to execute the trajectory needs to be more than npixels
	steeringCoord = (0, 0, -15) # x y z (mm) 
	# positive z goes away from xdcr (opposite IGT)
	# positive y goes towards xdcr cable
	# positive x goes right when looking at words on xdcr backplate (towards "SR53.2mm)
	
	# in motor coords: x->-y, y->-z , z-> -x
	
	
	# in repeat mode, on time + off time >=
	if (onTime + offTime <800):
		print('onTime + offTime must be greater than 800')
	else:
	
		# scale rel Ramp for input (which ramps to 100%)
		rampup = 100*relRamp/ampperc
		rampup = np.int(np.round(rampup))
		
		# scale amp from 0 to 244
		#ampscaled = ampperc/100*255
		ampscaled = 10
		ampscaled = np.round(ampscaled)
		ampscaled = np.int(ampscaled)
		

		# (1 phase, 1 frequency, 1 amplitude) = the same value for all channels
		shot1 = FUSTHON.PhaseShot (1, 1, 1)
		#shot1.setDuration (200, fus.gen.getMinTotalShotDuration(execMode)) # shot duration, shot delay, in us
		shot1.setDuration(onTime,offTime)
		shot1.setPhase (0, 0)               # set phase[0] = 0  (values in [0,255] = [0,360]deg)
		shot1.setFrequency (0, 1000000)     # set frequency[0] = 1 MHz
		shot1.setAmplitude (0, ampscaled)         # set amplitude[0] = 128 (half amplitude)
		
		# add ramp to shot
		print('max ramp duration:',fus.gen.getMaxRampDuration())
		fus.gen.setShotRampDuration (True, rampup)	# set the ramp up time to 100% amplitude to 100 us
		fus.gen.setShotRampDuration (False, rampup)	# set the ramp down time from 100% amplitude to 140 us
# 		print ("starting ramp: %d us" % fus.gen.readShotRampDuration(True))
# 		print ("ending ramp  : %d us" % fus.gen.readShotRampDuration(False))

		# get steering phases and Amps
		# Creates and initializes the transducer object used to compute the phases in shots
		transducerFile = "ATAC_config_v2.ini"
		trans = transducerXYZ.Transducer()
		if not trans.load(transducerFile):
			print ("Error: can not load the transducer definition from " + transducerFile)
			exit(1)
		trans.computePhases (shot1, steeringCoord)
		
		traj.addShot (shot1)
		# Only one shot in REPEAT mode.

		trajBuffer = 1
		execDelayUs = 0  # must be 0 in REPEAT mode (usually performs like this is 100)

		# Send and execute the trajectory
		fus.gen.sendTrajectory (trajBuffer, traj, execMode)
		fus.gen.executeTrajectory (trajBuffer, execCount, execDelayUs)
		listener.waitExecution()
	
		# Check execution result (success or failure).
		listener.printExecResult()
	
		# There is no ShotResult in REPEAT mode.

except Exception as why:
	print ("Exception: "+str(why))

fus.unregisterListener(listener)
fus.disconnect()
