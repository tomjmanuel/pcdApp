import FUSTHON
import utils as utils
import numpy as np
import transducerXYZ

# generator variables
fus = FUSTHON.FUS()
listener = utils.ExecListener()
fus.registerListener(listener)
trans = transducerXYZ.Transducer()
genIsConnected = 0                                         # track if generator is connected
shot = FUSTHON.PhaseShot(1, 1, 1)                         # shot variable (will get updated by updateTraj
channels = []
traj = []
execMode = FUSTHON.ElecExecMode.NORMAL
fusFile = 'D:/pcdApp/ATAC_config_v2.ini'
trigMode = FUSTHON.TriggerMode.ONE_PULSE_FOR_EVERYTHING

# VERBOSE, ERROR, INFO
fus.setLogLevel (FUSTHON.LogLevel.INFO)  # set max details

#utils.initLog(fus, 'logFile')
fus.enableLogStderr (True)
#fus.setLogFile ("D:/pcdApp/logfiles/log") # enable write to file
# only accept log messages with a level at least equal to info


# fus variables
PulseLengthVar = 20
PrfVar = 1
FreqVar = 1
AmpVar = 10
steeringCoord = (0,0,0)

if not trans.load(fusFile):
	print("Error: can not load the transducer definition from " + fusFile)
	exit(1)

# connect to generator
genIsConnected = utils.connect(fus)


# first create the shot and trajectory
onTime = int(PulseLengthVar)*1000
channels = fus.gen.getChannelCount()
traj = FUSTHON.ElectronicTrajectory(channels)
# compute offtime to fill the rest of the prf
# maybe that will handle the timing of everything...
totTime = (1/float(PrfVar) )*1000000 # total time per pulse in us (offtime plus ontime)
computerLag = 400 * 1000 # lag time to allow computation and display of spectral stuff etc (600 ms seems to work)
offTime = totTime-onTime - computerLag
shot.setDuration(onTime, int(offTime))
shot.setPhase(0, 0)  # set phase[0] = 0  (values in [0,255] = [0,360]deg)
freq = int(float(FreqVar)*1000000)
shot.setFrequency(0, freq)  # set frequency[0] = 1 MHz
print('frequency (Hz): ')
print(freq)
shot.setAmplitude(0, int(AmpVar))

# get steering phases
trans.computePhases(shot, steeringCoord)
traj.clear()
traj.addShot(shot)

# arm picoscope
#Pico.runBlock()
# send trajectory (contains latests amplitude)
fus.gen.sendTrajectory(1, traj, execMode)

#%%
fus.gen.executeTrajectory(1, 1, 0) # args: traj buffer, n pulses, execDelay
listener.waitExecution()
#Pico.waitForFinish()
listener.printExecResult()

#%% disconnect to generator
fus.unregisterListener(listener)
fus.disconnect()
