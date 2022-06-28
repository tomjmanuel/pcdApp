"""
This is the page for pcd app initialization.
It will perform things like connecting to generator and picoscope.
It will also program the pulses.

You can open the therapy page from this page. Opening attempt will check that
everything is connected and specicfied as it should be first.
"""

import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk
from numpy import round
import matplotlib
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
from time import sleep
import threading
from scipy.io import (loadmat, savemat)
from scipy.signal import resample
from runPicoSingleChannel import runPico as Pico
import FUSTHON
import utils as utils
import numpy as np
import transducerXYZ

class PcdApp(tk.Tk):

    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)
        self.resizable(0, 0)

        # dev puposes only- grab simulated data
        # load in developement data
        # variables = {'dataFull': dataFull, 'baselines': baselines, 'sampRate': sampRate}
        '''
        self.devData = loadmat('devData.mat')
        self.devDataFull = self.devData['dataFull']
        self.devDataFull = self.devDataFull[10:-1, :]
        self.devBaselines = self.devData['baselines']
        self.devSampRate = self.devData['sampRate']'''

        # initialization variables
        self.FreqVar = tk.StringVar(value="1")          # MHz
        self.PrfVar = tk.StringVar(value="1")           # Hz
        self.duration = tk.StringVar(value="180")       # (s) therapy duration
        self.AmpVar = tk.StringVar(value="9")          # Amp variable (0 to 255)
        self.AmpInc = tk.StringVar(value="2")           # Amp (change value)
        self.nAmps = tk.StringVar(value="5")            # n amps for baseline collection (sets range)
        self.PulseLengthVar = tk.StringVar(value="10")  # ms
        self.ampVec = []                                # vector with ampVec strings
        self.ampVecString = tk.StringVar()              # string with concatenated amp vecs for display
        self.fusFile = tk.StringVar(value='D:/pcdApp/ATAC_config_v2.ini')  # path + file to transducer config file (xdcr.ini)
        self.saveDir = tk.StringVar(value='D:/pcdApp/Data')  # path to save picoscope data
        self.steerX = tk.StringVar(value="0")
        self.steerY = tk.StringVar(value="0")
        self.steerZ = tk.StringVar(value="0")
        self.steeringCoord = (0,0,0)     # steering [mm] (x,y,z) with +z away from ATAC and towards 650 kHz

        # therapy variables
        self.spectData = np.array([])                                # fft vs time data from pcd
        self.spectImage = np.array([])                               # image representation of spectrogram
        self.nPulses = int(float(self.PrfVar.get()) * int(self.duration.get()) )   # number of pulses (computed from PRF and duration
        self.ICvec = np.array([])                                    # inertial caviation dose
        self.SCvec = np.array([])                                    # stable cavitation dose
        self.curr = int(0)                                              # iter value that tracks which shot we are on
        self.emergencyStop = 0                                          # flag to stop therapy if you push the stop button
        self.aspect = 30                                                # aspect ratio on spectrogram imshow
        self.nblave = 15                                                 # number of baselines to average for each amp
        self.ampIndex = int(round(int(self.nAmps.get())/2)-1)           # increases and decreases by one when amp is increased or decreased, initialize in middle of range
        self.baselinesCollected = 0                                     # set to 1 if baselines are collected, reset to zero when parameters are updated
        self.ampVsTime = []                                             # this will be a list that has the amp used for each pulse (tracks chaning amps through therapy)
        self.rawData = []
        self.therapyRunning = 0

        # picoscope variables
        self.Pico = []                                                  # object for interfacing with picoscope (initialized in connectPico)
        self.timebase = 4  # 9-> dt = 96                                # sets the sample interval
        self.recordTime = 500E-6                                        # how long the scope records
        self.vRange = "PS5000A_10V"                                     # voltage range for picoscope, try 10,20,50,100,200MV or 1 2 5 10V
        self.sampleInterval = (self.timebase - 3) / 62500000                 # dt / samp
        self.postTrigSamps = np.int(np.round(self.recordTime / self.sampleInterval))  # n samples
        self.picoIsConnected = 0
        print('postTrigSamps')
        print(self.postTrigSamps)

        # generator variables
        self.fus = FUSTHON.FUS()
        self.listener = utils.ExecListener()
        self.fus.registerListener(self.listener)
        self.trans = transducerXYZ.Transducer()
        self.genIsConnected = 0                                         # track if generator is connected
        self.shot = FUSTHON.PhaseShot(1, 1, 1)                         # shot variable (will get updated by updateTraj
        self.channels = []
        self.traj = []
        self.execMode = FUSTHON.ElecExecMode.NORMAL
        self.trigMode = FUSTHON.TriggerMode.ONE_PULSE_FOR_EVERYTHING
        utils.initLog(self.fus,'logfiles/logFile')
        self.fus.setLogLevel(FUSTHON.LogLevel.ERROR)  # only log errors

        # fft processing
        #self.sampRate = self.devSampRate[0]
        self.sampRate = int(1/self.sampleInterval)
        self.freqpoints = int(self.postTrigSamps/2)                                                             # number of points in single sided fft
        self.dsf = 10                                                                              # downsample spectrogram for display
        self.freqCrop = 5                                                                           # 2: 50% (only display first 50% of spectrum)
        self.freqRes = self.sampRate / (self.freqpoints * 2)                                        # sample rate / number of time points
        self.freqVec = self.freqRes*np.arange(np.round(self.freqpoints/self.freqCrop)) / 1000000          # (MHz) freq axis for line plot (cropped but not downsampled)
        self.npointscropped = int(round(len(self.freqVec) / self.dsf))
        #self.freqVecDS = resample(self.freqVec, self.npointscropped)                                # (MHz) freq axis for spectrogram (cropped and downsampled)
        self.freqVecDS = self.freqVec[0::self.dsf]
        self.freqMask = np.array([])                                                             # used to compute SC
        self.ICMask = np.array([])                                                               # ones between 1st and 2nd harmonic
        self.baselines = np.array([])                                                            # array to store baseline spectrums
        self.rawBaselines = []
        self.baselineSCIC = np.array([])

        # setup app window size with variables based on screen resolution
        ww = self.winfo_screenwidth()    # screen width px
        hh = self.winfo_screenheight()  # screen height px

        self.wa = round(ww*0.5)  # app width
        self.ha = round(hh*0.5)  # app height
        pad = 5    # common pad val

        # main frame has two columns of equal width, 1 row
        # column 1 is all FUS parameters
        # column 2 is generator and picoscope connections
        self.main_frame = tk.Frame(self, bg="#323232", height=self.ha, width=self.wa)
        self.main_frame.pack_propagate(0)
        self.main_frame.pack(fill="both", expand="true")

        # create the FUS options frame
        self.fusframe = tk.Frame(self.main_frame, bg="#323232", height=self.ha, width=round(self.wa/2))
        self.fusframe.grid(row=0, column=0)
        self.fusframe.grid(padx=pad, pady=pad)
        self.fusframe.grid_propagate(False)

        # create the frame on right that holds gena and pico frames
        rightframe = tk.Frame(self.main_frame, bg="#323232", height=self.ha, width=round(self.wa/2))
        rightframe.grid(row=0, column=1)
        rightframe.grid(padx=pad, pady=pad)

        # create the generator frame
        self.genframe = tk.Frame(rightframe, bg="#323232", height=round(self.ha/2), width=round(self.wa/2))
        self.genframe.grid(row=0, column=0)
        self.genframe.grid(padx=pad, pady=pad)
        self.genframe.grid_propagate(False)

        # create the picoscope frame
        self.picoframe = tk.Frame(rightframe, bg="#323232", height=round(self.ha/2), width=round(self.wa/2))
        self.picoframe.grid(row=1, column=0)
        self.picoframe.grid(padx=pad, pady=pad)
        self.genframe.grid_propagate(False)

        # create the therapy frame (full therapy window)
        self.therframe = tk.Toplevel(bg="#000000", height=round(self.ha*1.5), width=round(self.wa*1.5))
        self.therframe.resizable(0, 0)
        self.therframe.title("PCD app: Therapy Page")

        # create the left therapy frame (has spectrogram and IC SC plots
        self.lefttherframe = tk.Frame(self.therframe, bg="#c6c1b9", height=round(self.ha*1.5), width=round(self.wa))
        self.lefttherframe.grid(row=1, column=0)
        self.lefttherframe.grid(padx=pad, pady=pad)

        # create the right therapy frame (has line plot and amp controls)
        self.righttherframe = tk.Frame(self.therframe, bg="#323232", height=round(self.ha*1.5), width=round(self.wa/2))
        self.righttherframe.grid(row=1, column=1)
        self.righttherframe.grid(padx=pad, pady=pad)

        # fill frames
        self.fillFus()
        self.fillGen()
        self.fillPico()

        # Lock settings and open therapy page button
        therButt = tk.Button(rightframe, text='Go to therapy', command=self.openTherapy, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))
        therButt.grid(row=2, column=0)

        # initialize and display spectrogram image (empty at first)
        self.spectFig = Figure(figsize=(3, 2), dpi=round(self.wa/4), facecolor="#323232")
        self.updateSpectrogram()
        self.spectFigPlt = self.spectFig.add_subplot(111)
        # self.spectFigPlt.plot([1, 2, 3, 4, 5, 6, 7, 8], [5, 6, 1, 3, 8, 9, 3, 5])
        self.spectFigPlt.imshow(self.spectImage, aspect=self.aspect, interpolation="none", extent=[0, self.nPulses, self.freqVecDS[-1], 0])
        self.SpectCanvas = FigureCanvasTkAgg(self.spectFig, master=self.lefttherframe)
        self.SpectCanvas.draw()
        self.SpectCanvas.get_tk_widget().grid(row=0, column=0)

        # initialize and display IC and SC plot (empty at first)
        self.icFig = Figure(figsize=(3, 2), dpi=round(self.wa/4), facecolor='#0e289a')
        self.updateIcSc()
        self.icFigPlt = self.icFig.add_subplot(111)
        self.icFigPlt.plot(self.ICvec)
        self.icFig.tight_layout()
        self.SCcanvas = FigureCanvasTkAgg(self.icFig, master=self.lefttherframe)
        self.SCcanvas.draw()
        self.SCcanvas.get_tk_widget().grid(row=1, column=0)

        # initialize and display line plot of spectrum
        # add a frame for this
        self.lpframe = tk.Frame(self.righttherframe, bg="#c6c1b9", height=round(self.ha), width=round(self.wa/2))
        self.lpframe.grid(row=0, column=0)
        self.lpframe.grid(padx=pad, pady=pad)
        self.lpframe.grid_propagate(0)
        self.lpFig = Figure(figsize=(2, 2),  dpi=round(self.wa/4), facecolor='#0e289a')
        self.lpFigPlt = self.lpFig.add_subplot(111)
        self.lpFigPlt.plot(self.spectData[0:len(self.freqVec), self.curr], self.freqVec)  # x axis abs(fft) y axis freq
        self.lpFig.tight_layout()
        self.lpcanvas = FigureCanvasTkAgg(self.lpFig, master=self.lpframe)
        self.lpcanvas.draw()
        #self.lpcanvas.get_tk_widget().grid(row=0, column=0)
        self.lpcanvas.get_tk_widget().pack(ipadx=10, ipady=10)

        # initilialize and fill therapy controls panel
        # create the right therapy frame (has line plot and amp controls)
        self.controlframe = tk.Frame(self.righttherframe, bg="#323232", height=round(self.ha/2+self.ha/4), width=round(self.wa/2))
        self.controlframe.grid(row=1, column=0)
        self.controlframe.grid(padx=pad, pady=pad)
        self.controlframe.grid_propagate(0)
        self.fillCont()

        # create frequency mask that will help process IC and SC vectors
        self.createFreqMask()

        # hide therapy frame at first
        self.therframe.withdraw()
        self.main_frame.focus()

    def updateTraj(self):
        # first create the shot and trajectory
        onTime = int(self.PulseLengthVar.get())*1000
        self.channels = self.fus.gen.getChannelCount()
        self.traj = FUSTHON.ElectronicTrajectory(self.channels)
        # compute offtime to fill the rest of the prf
        # maybe that will handle the timing of everything...
        totTime = (1/float(self.PrfVar.get()) )*1000000 # total time per pulse in us (offtime plus ontime)
        computerLag = 400 * 1000 # lag time to allow computation and display of spectral stuff etc (600 ms seems to work)
        offTime = totTime-onTime - computerLag
        self.shot.setDuration(onTime, int(offTime))
        self.shot.setPhase(0, 0)  # set phase[0] = 0  (values in [0,255] = [0,360]deg)
        freq = int(float(self.FreqVar.get())*1000000)
        self.shot.setFrequency(0, freq)  # set frequency[0] = 1 MHz
        self.shot.setAmplitude(0, int(self.AmpVar.get()))

        # get steering phases
        self.trans.computePhases(self.shot, self.steeringCoord)
        self.traj.clear()
        self.traj.addShot(self.shot)

    def createFreqMask(self):
        self.freqMask = np.zeros((len(self.freqVec), 1))
        self.ICMask = np.zeros((len(self.freqVec), 1))
        # freqmask is a logically array that is 1's in the frequency bins (1 Mhz 2 MHz, 3 MHz)
        # also create an IC mask between 1st and 2nd harmonic
        #ws = 5  # size of frequency bin (hz) (it will be +/- ws)
        wsPix = 5 # int(round(ws/self.freqRes))  # number of points that are equivalent to ws
        numWin = 3     # number of harmonics to incluse (starts at fundamental)
        for i in range(numWin):
            freqCent = int(self.FreqVar.get())*1000000 / self.freqRes  # center of fundamental in samples
            freqCent = int(round(freqCent))
            self.freqMask[(freqCent*(i+1) + freqCent)-wsPix:(freqCent*(i+1) + freqCent)+wsPix, 0] = 1

        # also add in 1.5, 0.5, and 2.5 f0
        onepfive = int(round(freqCent*1.5))
        zeropfive = int(round(freqCent*0.5))
        twopfive = int(round(freqCent * 2.5))
        self.freqMask[onepfive-wsPix: onepfive+wsPix, 0] = 1
        self.freqMask[zeropfive - wsPix: zeropfive + wsPix, 0] = 1
        self.freqMask[twopfive - wsPix: twopfive + wsPix, 0] = 1

        # compute ICMask (1 to 2 MHz
        freqCent = int(self.FreqVar.get()) * 1000000 / self.freqRes  # center of fundamental in samples
        begin = int(freqCent + wsPix*2)
        fin = int(freqCent*2 - wsPix*2)
        self.ICMask[begin:fin,0] = 1

        # remove 1.5 f0 from IC vec
        self.ICMask[onepfive - wsPix: onepfive + wsPix, 0] = 0

    def do_therapy(self):
        # here is the run loop for the therapy
        # what all has to happen inside this loop?
            # shoot a pulse and receive data (pulseEcho)
            # compute and display spectrogram (updateSpectrogram)
            # compute IC and SC and plot that (updateICSC)
        self.emergencyStop = 0
        self.therapyRunning = 1

        # check if baselines have been collected
        if not self.baselinesCollected:
            print ('havent collected baselines')
            self.emergencyStop = 1

        self.curr = 0
        self.nPulses = int(round(float(self.PrfVar.get()) * int(self.duration.get())))
        while self.curr < self.nPulses and not self.emergencyStop:
            # these may have to run in seperate threads we'll see
            self.updateTraj()           # update trajectory with new shot that has current amplitude
            self.pulseEcho()            # shoot your shot and collect some data yo
            self.updateSpectrogram()    # update the spectrogram to include new data
            self.updateIcSc()           # update the ICSC plot to include new data
            self.curr = self.curr+1     # update the pulse you're on
            self.ampVsTime.append(self.AmpVar.get())
            self.Pico.clearData() # remove data from picoscope
        self.therapyRunning = 0

    def do_baselines(self):
        # here is the loop to collect a baseline for every amp to be tested
        # it also averages them in fft space and puts them into a baselines variable for later subtraction
        originalAmp = self.AmpVar.get()
        origampind = self.ampIndex

        # set ampVar to lowest amp
        minAmp = self.ampVec[0]
        minAmp = float(minAmp)
        minAmp = round(minAmp)
        minAmp = int(minAmp)
        minAmp = str(minAmp)
        self.AmpVar.set(minAmp)
        self.baselines = np.zeros((self.freqpoints, int(self.nAmps.get()))) # freqpoints by number of amps
        self.baselineSCIC = np.zeros((2, int(self.nAmps.get())))
        for ii in range(int(self.nAmps.get())):
            print('collecting baseline for Amp = ' + self.AmpVar.get())
            for jj in range(self.nblave):
                self.updateTraj()  # update trajectory
                self.Pico.runBlock()
                self.fus.gen.sendTrajectory(1, self.traj, self.execMode)
                self.fus.gen.executeTrajectory(1, 1, 0)  # args: traj buffer, n pulses, execDelay
                self.listener.waitExecution()
                self.Pico.waitForFinish()
                self.listener.printExecResult()
                sleep(0.1)
            # compute fft of baseline and average it
            self.baselines[:, ii] = self.procBaseline(self.Pico.getDataA())

            # compute IC and SC values for this baseline and store it for future subtraction
            # baselineSCIC is 2 by nBL with 1 being SC, 2 being IC on first dimension
            self.getICSC_Baselines(self.baselines[:,ii], ii)

            # display the last baseline to check if clipping
            self.displayBaseline(self.Pico.getDataA())

            self.Pico.clearData() # clear data from picoscope object
            # put baseline into a baselines variable
            # dev is working with self.baselines
            self.increaseAmp() # increase with each iteration
            sleep(0.1)
        # mark baselines as collected
        self.baselinesCollected = 1

        # return amp var to original value
        self.AmpVar.set(originalAmp)
        self.ampIndex = origampind  # also reset amp index
        #

    def displayBaseline(self, data):
        # the goal is to find a portion of the signal that is maximum and plot it in a way that would make
        # clipping visually apparent
        self.lpFigPlt.cla()
        data = np.asarray(data)
        index = np.argmax(data[0, :]) # index is where the max is so we can plot around that
        # check to make sure we can plot there and up 1000 (not at end)
        if index + 250 < len(data[0,:]):
            self.lpFigPlt.plot(data[0,index:index+250])
        else:
            self.lpFigPlt.plot(data[0,-250:index+-1]) # just plot the last 1000 samples
        self.lpcanvas.draw_idle()

    def procBaseline(self, data):
        # compute spectrum of baselines and then average
        spec = np.fft.fft(data,axis=1)
        avespec = np.average(spec, axis=0)
        return(np.abs(avespec[0:self.freqpoints]))

    def pulseEcho(self):
        # arm picoscope
        self.Pico.runBlock()
        # send trajectory (contains latests amplitude)
        self.fus.gen.sendTrajectory(1, self.traj, self.execMode)
        self.fus.gen.executeTrajectory(1, 1, 0) # args: traj buffer, n pulses, execDelay
        self.listener.waitExecution()
        self.Pico.waitForFinish()
        self.listener.printExecResult()

    def stopTherapy(self):
        self.emergencyStop = 1
        #

    def fillCont(self):

        # Fill the control panel ################################
        cont_label = tk.Label(self.controlframe, text='Control Panel', font=('calibre', 20, 'bold'), bg='#323232', fg='#FFFFFF')

        # collect baselines button
        #basebutt = tk.Button(self.controlframe, text='Collect Baselines', command=lambda: threading.Thread(target=self.do_baselines).start(), height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))
        basebutt = tk.Button(self.controlframe, text='Collect Baselines',
                             command=self.do_baselines, height=1, width=24,
                             pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # Increase and decrease amp buttoms
        incbutt = tk.Button(self.controlframe, text=' + AMP', command=self.increaseAmp, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))
        decbutt = tk.Button(self.controlframe, text=' - AMP', command=self.decreaseAmp, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # Amp display label and label
        ampdisp = tk.Label(self.controlframe, text='Current Amp: ', font=('calibre', 10, 'normal'), bg='#323232', fg='#FFFFFF')
        amplab = tk.Label(self.controlframe, textvariable=self.AmpVar, font=('calibre', 7, 'normal'), bg='#323232', fg='#FFFFFF')

        # run therapy button
        runbutt = tk.Button(self.controlframe, text='Run therapy', command=lambda: threading.Thread(target=self.do_therapy).start(), height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # stop therapy button
        stopbutt = tk.Button(self.controlframe, text='Stop therapy', command=self.stopTherapy, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # save Data button
        savebutt = tk.Button(self.controlframe, text='Save data', command=self.saveData, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # clear Data button
        clearbutt = tk.Button(self.controlframe, text='Clear data', command=self.clearData, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # Modify button (repopens init page)
        modbutt = tk.Button(self.controlframe, text='Modify parameters', command=self.showInit, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # display amplitudes you collected baselines with
        ampvec_label = tk.Label(self.controlframe, text='Available amplitudes', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        ampvec_disp = tk.Label(self.controlframe, textvariable=self.ampVecString, font=('calibre', 10, 'normal'), bg='#323232', fg='#FFFFFF', wraplength="1.7i")

        # place erthing in grid
        cont_label.grid(row=0, column=0, columnspan=2)
        basebutt.grid(row=1, column=0)
        decbutt.grid(row=2, column=0)
        incbutt.grid(row=2, column=1)
        ampdisp.grid(row=3, column=0)
        amplab.grid(row=3, column=1)
        runbutt.grid(row=4, column=0)
        stopbutt.grid(row=4, column=1)
        savebutt.grid(row=5, column=0)
        clearbutt.grid(row=5, column=1)
        ampvec_label.grid(row=6, column=0)
        ampvec_disp.grid(row=6, column=1, columnspan=2)
        modbutt.grid(row=7, column=0)

    def increaseAmp(self):
        print(self.AmpVar.get())
        maxAmp = self.ampVec[-1]
        maxAmp = float(maxAmp)
        maxAmp = round(maxAmp)
        maxAmp = int(maxAmp)
        maxAmp = str(maxAmp)
        if self.AmpVar.get() != maxAmp:  # true if already at max ampVec value
            foo = int(self.AmpVar.get()) + int(self.AmpInc.get())
            self.AmpVar.set(str(foo))
            self.ampIndex = self.ampIndex + 1
        else:
            print('Reached max amp')

    def saveData(self):
        print('saving data')
        f = fd.asksaveasfilename(initialdir=self.saveDir.get(), filetypes=[("*.mat file", "*.mat")], defaultextension=".mat")
        mdic = {"ampsUsed": self.ampVsTime, "SpectData": self.spectData, "SpectImage": self.spectImage,
                "freqAxis": self.freqVec, "freqAxisDS": self.freqVecDS, "sampRate": self.sampRate,
                "prf": self.PrfVar.get(), "duration": self.duration.get(), "pulselength": self.PulseLengthVar.get(),
                "frequency": self.FreqVar.get(), "steering": self.steeringCoord, "baselines": self.baselines,
                "rawdata": self.rawData, "ICVec": self.ICvec, "SCVec": self.SCvec, "ICmask": self.ICMask, "SCmask": self.freqMask}
        savemat(f, mdic)
        self.therframe.deiconify()

    def showInit(self):
        self.main_frame.focus()
        self.main_frame.pack(fill="both", expand="true")
        self.therframe.withdraw()
        self.clearData()

    def clearData(self):
        # clear data does not clear baselines
        # this enables recollecting data after starting a therapy but if somethings goes wrong halfway through
        # that way you still have prebubble baselines
        # to clear baselines, just recolllect new baselines or restart program

        print('clearing data')
        self.curr = 0
        self.Pico.clearData()
        self.spectData = np.array([])                                # fft vs time data from pcd
        self.spectImage = np.array([])
        self.rawData = []
        self.ICvec = np.array([])                                    # inertial caviation dose
        self.SCvec = np.array([])                                    # stable cavitation dose
        self.curr = int(0)                                              # iter value that tracks which shot we are on
        self.emergencyStop = 0                                          # flag to stop therapy if you push the stop button
        self.ampVsTime = []

    def decreaseAmp(self):
        print(self.AmpVar.get())
        minAmp = self.ampVec[0]
        minAmp = float(minAmp)
        minAmp = round(minAmp)
        minAmp = int(minAmp)
        minAmp = str(minAmp)
        if self.AmpVar.get() != minAmp:  # true if already at min ampVec value
            foo = int(self.AmpVar.get())- int(self.AmpInc.get())
            self.AmpVar.set(str(foo))
            self.ampIndex = self.ampIndex - 1
        else:
            print('already at min amplitude')

    def updateSpectrogram(self):
        # update the spectrogram image (nothing to do with data collection)
        # this gets called on initialization to fill the plot with zeros
        # it then gets called on every pulse event to update the spectrogram plot
        self.nPulses = int(round(float(self.PrfVar.get()) * int(self.duration.get())))
        if self.spectImage.size == 0:  # true at initialization
            #self.spectImage = np.random.randn(int(self.nPulses), self.freqpoints)
            self.spectImage = np.zeros((self.npointscropped, int(self.nPulses)))
            self.spectData = np.zeros((self.freqpoints, int(self.nPulses)))
        else:

            # if therapy is running compute spectrum
            # do math to generate image representation of spectrogram
            if self.therapyRunning:
                self.computeSpectrum()
        #


    def computeSpectrum(self):
        # this function gets called by updateSpectrogram
        # it compute the fft of the latest data point and places that spectrum in the self.spectData variable
        print('computeSpectrum')
        #vec = self.devDataFull[self.curr, :]  # time vector of current data
        vec = self.Pico.getDataA()
        self.rawData.append(vec)

        # could have apodization here by (vec * apodization)
        Fvec = np.fft.fft(vec)  # raw spectrum for this timepoint

        # implement baseline subtraction here based on current amplitude
        FvecSub = np.abs(Fvec[0, 0:self.freqpoints]) - self.baselines[:, self.ampIndex]

        # insert into spect data
        self.spectData[:, self.curr] = np.log10(np.abs(FvecSub[0:self.freqpoints])+.001)

        # downsample for image representation
        FvecSubResamp = resample(self.spectData[:, self.curr], int(self.freqpoints / self.dsf))
        # place resampled subtracted vector into image (use freq crop here)
        self.spectImage[:, self.curr] = FvecSubResamp[0:len(self.freqVecDS)-1]

        # get upper and lower bounds for spectImage contrast
        upperBound = np.max(FvecSubResamp)
        lowerBound = np.average(FvecSubResamp)
        lowerBound = lowerBound + np.std(FvecSubResamp)

        #display
        self.spectFigPlt.cla()
        self.spectFigPlt.imshow(self.spectImage, vmax=upperBound, vmin=lowerBound, aspect=self.aspect, interpolation="none", extent=[0, self.nPulses, self.freqVecDS[-1], 0])
        self.SpectCanvas.draw_idle()
        self.lpFigPlt.cla()
        self.lpFigPlt.plot(self.spectData[0:len(self.freqVec), self.curr], self.freqVec)
        self.lpFigPlt.set_xlim([lowerBound, upperBound])

        # optionaly display the bins used for SC and IC calculation
        #self.lpFigPlt.plot(self.ICMask[0:len(self.freqVec), 0], self.freqVec)
        #self.lpFigPlt.plot(self.freqMask[0:len(self.freqVec), 0], self.freqVec)

        # refresh
        self.lpcanvas.draw_idle()


    def getICSC_Baselines(self, vec,ind):
        # takes fft.fft of raw baseline data (vec)
        # index tells which baseline you are on
        # takes its logarithm and finds the energy in SC and IC bands
        vec2 = np.log10(np.abs(vec[0:self.freqpoints]) + .001)

        # SC
        foo = self.freqMask[:, 0] * vec2[0:len(self.freqMask)]  # multiply spectData by freqMask (1s within harmonic windows)
        self.baselineSCIC[0, ind] = np.sum(foo[:]) / np.sum(self.freqMask)  # sum and scale by number of points in mask
        # IC
        foo = self.ICMask[:, 0] * vec2[0:len(self.ICMask)]  # multiply spectData by IC mask
        self.baselineSCIC[1, ind] = np.sum(foo[:]) / np.sum(self.ICMask)

    def updateIcSc(self):
        # update the IC and SC data
        if self.ICvec.size == 0: # true on initialization
            self.ICvec = np.zeros((int(self.nPulses), 1))
            self.SCvec = np.zeros((int(self.nPulses), 1))
        else:

            # if therapy is running
            if self.therapyRunning:

                # I want SC and IC to be in the same scale relatively
                # one idea is to scale them such that they are scaled by number of bins included in calculation

                # get noise floor (average of everything not in SC or IC window
                notSCmask = np.abs(self.freqMask[:, 0] -1) + np.abs(self.ICMask[:,0] -1)
                foo = notSCmask * self.spectData[0:len(self.freqMask), self.curr] # opposite of freq mask times spect data
                noisefloor = np.sum(foo[:]) / np.sum(notSCmask)

                # SC
                foo = self.freqMask[:, 0] * self.spectData[0:len(self.freqMask), self.curr] # multiply spectData by freqMask (1s within harmonic windows)
                #self.SCvec[self.curr] = np.sum(foo[:]) / np.sum(self.freqMask) - self.baselineSCIC[0,self.ampIndex] # sum and scale by number of points in mask
                self.SCvec[self.curr] = np.sum(foo[:]) / np.sum(self.freqMask) - noisefloor
                #print(self.baselineSCIC[0,self.ampIndex])

                # IC
                foo = self.ICMask[:, 0] * self.spectData[0:len(self.ICMask), self.curr] # multiply spectData by IC mask
                #self.ICvec[self.curr] = np.sum(foo[:]) / np.sum(self.ICMask) - self.baselineSCIC[1,self.ampIndex]
                self.ICvec[self.curr] = np.sum(foo[:]) / np.sum(self.ICMask) - noisefloor
                #print(self.baselineSCIC[1, self.ampIndex])


                # display
                self.icFigPlt.cla()
                self.icFigPlt.plot(self.SCvec, label="SC dose")
                self.icFigPlt.plot(self.ICvec, label="IC dose")
                self.icFigPlt.legend(loc="upper right")
                self.SCcanvas.draw_idle()
        #


    def openTherapy(self):
        # first check that picoscope and generator are connected
        if self.genIsConnected and self.picoIsConnected:
            print('open therapy')
            self.therframe.deiconify()
            self.main_frame.pack_forget()
        else:
            if not self.genIsConnected:
                print('generator not connected')
            if not self.picoIsConnected:
                print('Picoscope not connected')

    def fillFus(self):
        # Fill the FUS panel ################################
        # FUS label
        fus_label = tk.Label(self.fusframe, text='FUS Panel', font=('calibre', 20, 'bold'), bg='#323232', fg='#FFFFFF')

        # PRF
        prf_label = tk.Label(self.fusframe, text='0.5 <= PRF (Hz) <= 2', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        prf_entry = tk.Entry(self.fusframe, textvariable=self.PrfVar, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')

        # Frequency
        freq_label = tk.Label(self.fusframe, text='Frequency (MHz)', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        freq_entry = tk.Entry(self.fusframe, textvariable=self.FreqVar, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')

        # therapy duration
        dur_label = tk.Label(self.fusframe, text='Therapy duration (s)', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        dur_entry = tk.Entry(self.fusframe, textvariable=self.duration, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')

        # PulseLengthVar
        plv_label = tk.Label(self.fusframe, text='Pulse length (ms)', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        plv_entry = tk.Entry(self.fusframe, textvariable=self.PulseLengthVar, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')

        # AmpVar
        amp_label = tk.Label(self.fusframe, text='Amplitude (0-255)', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        amp_entry = tk.Entry(self.fusframe, textvariable=self.AmpVar, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')

        # AmpInc
        ampInc_label = tk.Label(self.fusframe, text='Amp increment (0-255)', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        ampInc_entry = tk.Entry(self.fusframe, textvariable=self.AmpInc, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')

        # nAmps
        nAmps_label = tk.Label(self.fusframe, text='# of Amplitudes', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        nAmps_entry = tk.Entry(self.fusframe, textvariable=self.nAmps, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')

        # steering
        steer_labelX =  tk.Label(self.fusframe, text='Steering X [mm]', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        sx_entry = tk.Entry(self.fusframe, textvariable=self.steerX, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')
        sy_entry = tk.Entry(self.fusframe, textvariable=self.steerY, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')
        sz_entry = tk.Entry(self.fusframe, textvariable=self.steerZ, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8')
        steer_labelY = tk.Label(self.fusframe, text='Steering Y [mm]', font=('calibre', 10, 'bold'), bg='#323232',
                                fg='#FFFFFF')
        steer_labelZ = tk.Label(self.fusframe, text='Steering Z [mm]', font=('calibre', 10, 'bold'), bg='#323232',
                                fg='#FFFFFF')

        # placing the label and entry in the grid of the fus frame
        fus_label.grid(row=0, column=0, columnspan=2)
        freq_label.grid(row=1, column=0)
        freq_entry.grid(row=1, column=1)
        plv_label.grid(row=2, column=0)
        plv_entry.grid(row=2, column=1)
        dur_label.grid(row=3, column=0)
        dur_entry.grid(row=3, column=1)
        amp_label.grid(row=4, column=0)
        amp_entry.grid(row=4, column=1)
        ampInc_label.grid(row=5, column=0)
        ampInc_entry.grid(row=5, column=1)
        nAmps_label.grid(row=6, column=0)
        nAmps_entry.grid(row=6, column=1)
        prf_label.grid(row=7, column=0)
        prf_entry.grid(row=7, column=1)

        # get amplitudes and then display them in a label
        self.get_amps()
        ampvec_label = tk.Label(self.fusframe, text='Amplitudes', font=('calibre', 10, 'bold'), bg='#323232', fg='#FFFFFF')
        ampvec_label.grid(row=8, column=0)
        ampvec_disp = tk.Label(self.fusframe, textvariable=self.ampVecString, font=('calibre', 10, 'normal'), bg='#323232', fg='#90b8f8', wraplength="1.7i")
        ampvec_disp.grid(row=8, column=1, columnspan=2)

        # add steering
        steer_labelX.grid(row=9, column=0)
        sx_entry.grid(row=9, column=1)
        steer_labelY.grid(row=10, column=0)
        sy_entry.grid(row=10, column=1)
        steer_labelZ.grid(row=11, column=0)
        sz_entry.grid(row=11, column=1)

        # add a button to refresh values when user inputs changes
        butt = tk.Button(self.fusframe, text="Apply changes", command=self.get_amps, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))
        butt.grid(row=12, column=0)


    def fillGen(self):
        # Fill the generator panel ################################
        # gen label
        gen_label = tk.Label(self.genframe, text='Generator Panel', font=('calibre', 20, 'bold'), bg='#323232', fg='#FFFFFF')

        # fus config file picker
        fusfilebutt = tk.Button(self.genframe, text='Select new FUS config file', command=self.getFusFile, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # fusconfig file display label and label
        fusfiledisp = tk.Label(self.genframe, text='Fus config file', font=('calibre', 10, 'normal'), bg='#323232', fg='#FFFFFF')
        fusfilelab = tk.Label(self.genframe, textvariable=self.fusFile, font=('calibre', 7, 'normal'), bg='#323232', fg='#90b8f8')

        # canvas indicator light for connection
        gencanvas = tk.Canvas(self.genframe, bg="#323232", height=20, width=20, highlightthickness=0)
        genlight = gencanvas.create_oval(5, 5, 18, 18, fill="red")

        # connect to gen button
        connectgenbutt = tk.Button(self.genframe, text='Connect', command=lambda: self.connectGen(gencanvas, genlight), height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # connect to gen button
        disconnectgenbutt = tk.Button(self.genframe, text='Disconnect', command=lambda: self.disconnectGen(gencanvas, genlight), height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # place erthing in grid
        gen_label.grid(row=0, column=0, columnspan=2)
        fusfiledisp.grid(row=2, column=0)
        fusfilelab.grid(row=2, column=1)
        fusfilebutt.grid(row=4, column=0)
        connectgenbutt.grid(row=5, column=0)
        gencanvas.grid(row=5, column=1)
        disconnectgenbutt.grid(row=6, column=0)

    def fillPico(self):
        # Fill the pico panel ################################
        # pico label
        pico_label = tk.Label(self.picoframe, text='Picoscope Panel', font=('calibre', 20, 'bold'), bg='#323232', fg='#FFFFFF')

        # canvas indicator light for connection
        picocanvas = tk.Canvas(self.picoframe, bg="#323232", height=20, width=20, highlightthickness=0)
        picolight = picocanvas.create_oval(5, 5, 18, 18, fill="red")

        # save data dir picker
        savebutt = tk.Button(self.picoframe, text='Select new save directory', command=self.getSaveDir, height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # save dir display label and label
        savedirdisp = tk.Label(self.picoframe, text='Save directory: ', font=('calibre', 10, 'normal'), bg='#323232', fg='#FFFFFF')
        savedirlab = tk.Label(self.picoframe, textvariable=self.saveDir, font=('calibre', 7, 'normal'), bg='#323232', fg='#90b8f8')

        # connect to pico button
        connectpicobutt = tk.Button(self.picoframe, text='Connect', command=lambda: self.connectpico(picocanvas, picolight), height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # disconnect to pico button
        disconnectpicobutt = tk.Button(self.picoframe, text='Disconnect', command=lambda: self.disconnectpico(picocanvas, picolight), height=1, width=24, pady=3, padx=3, bg='#aaaaaa', fg='#000000', font=('calibre', 10, 'normal'))

        # place erthing in grid
        pico_label.grid(row=0, column=0, columnspan=2)
        savedirdisp.grid(row=2, column=0)
        savedirlab.grid(row=2, column=1)
        savebutt.grid(row=4,column=0)
        connectpicobutt.grid(row=5, column=0)
        picocanvas.grid(row=5, column=1)
        disconnectpicobutt.grid(row=6, column=0)

    def getSaveDir(self):
        fn = fd.askdirectory( initialdir=self.saveDir.get())
        self.saveDir.set(fn)

    def connectGen(self, gencanvas, genlight):
        # load transducer file
        if not self.trans.load(self.fusFile.get()):
            print("Error: can not load the transducer definition from " + self.fusFile.get())
            exit(1)

        # connect to generator
        self.genIsConnected = utils.connect(self.fus)
        if self.genIsConnected:
            gencanvas.itemconfig(genlight, fill="green")
            print('generator connected')
        else:
            print('generator connection failed')

    def disconnectGen(self, gencanvas, genlight):

        # connect to generator
        self.fus.disconnect()
        gencanvas.itemconfig(genlight, fill="red")
        self.genIsConnected = 0
        print('generator disconnected')

    def connectpico(self, picocanvas, picolight):
        # connect to picoerator
        # check if already connected
        if self.picoIsConnected:
            print('already connected to picoscope')
        else:
            print('connect to picoscope')
            self.Pico = Pico(self.postTrigSamps, self.timebase, self.vRange)
            # need a check here to make sure it connected
            if self.Pico.checkConnected():
                picocanvas.itemconfig(picolight, fill="green")
                self.picoIsConnected = 1
            else:
                print('picoscope connection failed')
        #

    def disconnectpico(self, picocanvas, picolight):
        # connect to picoerator
        # check if already connected
        if not self.picoIsConnected:
            print('Picoscope is not connected')
        else:
            print('disconnect picoscope')
            self.Pico.disconnect()
            picocanvas.itemconfig(picolight, fill="red")
            self.picoIsConnected = 0
        #

    def getFusFile(self):
        fn = fd.askopenfilename()
        self.fusFile.set(fn)

    def quit_application(self):
        self.destroy()

    def get_amps(self):
        # this function takes the nAmps, AmpInc, and AmpVar and creates the list
        # of amplitudes to be used in background computation
        # it also updates steering coordinates and other values that have been changed

        # first check if nAmps is even. If so add one number to it
        if int(self.nAmps.get()) % 2 == 0:
            print('changing nAmps to odd')
            foo = int(self.nAmps.get())+1
            self.nAmps.set(str(foo))

        # compute start amp
        # start amp = Amp - ((nAmps-1)/2 )* ampInc
        AmpInc = int(self.AmpInc.get())
        startamp = int(self.AmpVar.get()) - ((int(self.nAmps.get())-1)/2)*AmpInc
        tempString = ''  # used to compute ampVecString
        self.ampVec = []

        for i in range(int(self.nAmps.get())):
            val = startamp + i*AmpInc
            self.ampVec.append(str(val))
            tempString = tempString + str(val) + ', '

        # remove comma at end
        tempString = tempString[0:-2]
        print(tempString)
        self.ampVecString.set(tempString)

        # update steering
        temp = list(self.steeringCoord)
        temp[0] = float(self.steerX.get())
        temp[1] = float(self.steerY.get())
        temp[2] = float(self.steerZ.get())
        self.steeringCoord = tuple(temp)
        print('new steering: ')
        print(self.steeringCoord)

        # update number of pulses and variables shaped by n pulses
        self.nPulses = int(float(self.PrfVar.get()) * int(self.duration.get()))
        self.spectImage = np.zeros((self.npointscropped, int(self.nPulses)))
        self.spectData = np.zeros((self.freqpoints, int(self.nPulses)))
        self.ICvec = np.zeros((int(self.nPulses), 1))
        self.SCvec = np.zeros((int(self.nPulses), 1))


# Call window
root = PcdApp()
root.title("PCD feedback app- Initialization page")
root.mainloop()

