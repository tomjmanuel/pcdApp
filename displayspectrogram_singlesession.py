# -*- coding: utf-8 -*-
"""
Created on Wed Sep 22 13:25:43 2021
tom 
this one just makes a spectrogram from a single session
this session may have the first few frames used for bubbles
This is following the BBBO procedure in rat on 9/21

@author: tomjm
"""

import SampleReader
from PIL import Image

noBubs = SampleReader.PCDReader('./therapy4/')
Bubs = SampleReader.PCDReader('./therapy4/')

apodization=SampleReader.numpy.hanning(noBubs.fft.size)
apodizationMean=sum(apodization)/float(noBubs.fft.size)

# Collect first 10 noBubs frames and average them to use for subtraction
bL = SampleReader.numpy.zeros((10, int(noBubs.fft.size/2+1)))
for ii in range(10):
    s = noBubs.readShot(0,ii,0)
    spectra = SampleReader.numpy.fft.fft(s[0:noBubs.fft.size]*apodization)
    bL[ii,:] = abs(spectra[0:int(noBubs.fft.size/2+1)]*apodizationMean)

bLave = SampleReader.numpy.average(bL,axis=0)
SampleReader.plt.plot(bLave)
SampleReader.plt.title('no bubbles')
SampleReader.plt.show()

## iterate through frames of the with Bubbles collection and store the subtracted spectrogram
# put baseline in first 10
spectrogram = SampleReader.numpy.zeros((int(Bubs.iterationCount()), int(noBubs.fft.size/2+1)))
for ii in range(int(Bubs.iterationCount())):
    if ii>9:
        s = Bubs.readShot(0,ii,0)
        spectra = SampleReader.numpy.fft.fft(s[0:Bubs.fft.size]*apodization)
        spectrogram[ii,:] = abs(spectra[0:int(Bubs.fft.size/2+1)]*apodizationMean)-bLave
    else:
        spectrogram[ii,:] = bL[ii,:]-bLave
        

#%% try to convert spectrogram to decibels
spectrogram[spectrogram<0]=0.0000000001
spectrogram = spectrogram/SampleReader.numpy.max(spectrogram)

#%%
sdb = 20*SampleReader.numpy.log10(spectrogram)
freq = SampleReader.numpy.arange((noBubs.fft.size / 2) + 1) / (float(noBubs.fft.size) / noBubs.scope.samplingRate)   # Frequency axis
        
#%% 
SampleReader.plt.plot(freq,sdb[160,:])
SampleReader.plt.xlabel('Hz')
SampleReader.plt.ylabel('dB')
SampleReader.plt.ylim(-70,0)
SampleReader.plt.title('PCD data, 80 s in')
SampleReader.plt.show()

#%% display spectrogram

sdbcrop = sdb
sdbcrop[sdbcrop<-40]=-40
sdbcrop[sdbcrop>-35]=-35
#SampleReader.plt.imshow(SampleReader.numpy.transpose(sdb),vmin=-60.0,vmax=-50,,aspect=.00001)
SampleReader.plt.imshow(SampleReader.numpy.transpose(sdbcrop),aspect=.1,extent=[0,SampleReader.numpy.floor(Bubs.iterationCount()/2),int(freq[-1]),0])
SampleReader.plt.colorbar()
SampleReader.plt.xlabel('Time (s)')
SampleReader.plt.ylabel('Frequency (Hz)')
SampleReader.plt.title('Spectrogram, Therapy 4')

#%% grab the amplitude the amp was driven at over therapy and plot it
amps = SampleReader.numpy.zeros((int(Bubs.iterationCount()+10),1))

#%%
for ii in range(int(Bubs.iterationCount()+10)):
    print(ii)
    if ii>222:
        amps[ii]=Bubs.amplitudeAt(ii-10)

#%%
SampleReader.plt.plot(amps)
SampleReader.plt.ylim(0, 15)
SampleReader.plt.ylabel('% Amp')
SampleReader.plt.xlabel('Frame (2 Hz)')
SampleReader.plt.title('Amplitude used during therapy')
#%% plot a no Bubs spectra
s = noBubs.readShot(0,0,0)
spectra = SampleReader.numpy.fft.fft(s[0:noBubs.fft.size]*apodization)
SampleReader.plt.plot(abs(spectra[0:int(noBubs.fft.size/2+1)]*apodizationMean))
SampleReader.plt.title('no bubbles')
SampleReader.plt.show()

# plot a Bubs spectra
s = Bubs.readShot(0,100,0)
spectra = SampleReader.numpy.fft.fft(s[0:Bubs.fft.size]*apodization)
SampleReader.plt.plot(abs(spectra[0:int(Bubs.fft.size/2+1)]*apodizationMean))
SampleReader.plt.title('bubbles')
SampleReader.plt.show()




''' display the first spectra
s=pcdreader.readShot(shotIndex,iteration,channelIndex)
spectra=numpy.fft.fft(s[0:pcdreader.fft.size]*apodization)
plt.plot(abs(spectra[0:int(pcdreader.fft.size/2+1)]*apodizationMean))
plt.title('first spectra')
plt.show()
'''
