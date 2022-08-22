%% Tom 07/07/22
% batch processing my data using my methods to compare with Pouliopolis
% nav to : C:\Users\tomjm\Documents\Projects\ATAC_xdcr\pcdapp\Data_compiled\withpcdapp
clear all
close all
fns = dir('*.mat');
nf = length(fns);

%%
for i=1:13
figure
%i=5;
fn = fns(i).name; % higher pressure at first then dropped down
%fn = 'try2_bubs.mat'; %
data = load(fn);
rawdata = data.rawdata;
prf = str2num(data.prf);
baselines = data.baselines; % alread fft but no log compress
%bLind = data.bLind;
bLind = data.ampIndexes+1;
bLind = round(bLind);
sampRate = data.sampRate;

%% compare zero pad fft
% dim = size(rawdata);
% cheb = repmat(chebwin(dim(3))',[dim(1), 1]);
% rawdataC = squeeze(rawdata).*cheb;
% Fraw = fft(squeeze(rawdata),dim(3)*2,2);
% Fraw = Fraw(:,1:floor(dim(3)));
% 
% % create freq axis
% freqpoints = floor(dim(3));
% freqRes = sampRate / (freqpoints*2);
% freqVec = double(freqRes).*(0:1:(freqpoints-1))./1E6;

%% try upsampling time domain
% dim = size(rawdata);
% rawdataUS = imresize(squeeze(rawdata),[dim(1) dim(3).*4]);
% FrawUS = fft(rawdataUS,dim(3)*4,2);
% FrawUS = FrawUS(:,1:floor(dim(3)*2));
% freqpoints = dim(3)*2;
% freqResUS = sampRate/(freqpoints*2);
% freqVecUS = double(freqRes).*(0:1:(freqpoints-1))./1E6;


%% first take the fft and generate a freq axis (no zero pad)
dim = size(rawdata);
%cheb = repmat(chebwin(dim(3))',[dim(1), 1]);
%rawdataC = squeeze(rawdata).*cheb;
Fraw = fft(squeeze(rawdata),dim(3),2);
Fraw = Fraw(:,1:floor(dim(3)/2));

% create freq axis
freqpoints = floor(dim(3)/2);
freqRes = sampRate / (freqpoints*2);
freqVec = double(freqRes).*(0:1:(freqpoints-1))./1E6;

%% make spectrogram
ind1Mhz = round(1E6 / freqRes);
ws = round(200E3 / freqRes);

% abs fft
FrawN = abs(Fraw); %./repmat(max(abs(Fraw),[],2),[1,freqpoints]);

% baseline subtraction
Fsub = zeros(size(Fraw));
for jj=1:dim(1)
    bL = baselines(:,bLind(jj));
    % subtract log normalized spectra with log normalized baseline of given
    % power
    Fsub(jj,:) = FrawN(jj,:) - bL';
    
    % cancel out band around 1 MHz
    %Fsub(jj,ind1Mhz-ws:ind1Mhz+ws) = mean(Fsub(jj,ind1Mhz.*4:ind1Mhz*6));
    
end

% can remove anything sub zero on first principles
Fsub(Fsub<0)=0;
timeExp = (0:1:dim(1)-1)./prf;
SpectImage = imgaussfilt(Fsub,3);

%%
subplot(4,1,[1 2])
Clim = [0 (mean(Fsub(:))+2.*std(Fsub(:)))];
imagesc(timeExp,freqVec,SpectImage',Clim)
colormap('gray')
ylim([0 8])
xlabel('time (s)')
ylabel('MHz')
set(gcf,'color','white')
title(fn, 'Interpreter', 'none')

%% receate SC and IC mask (skip if on data collected after 021422
% now make the IC and SC plots
% this data was collected prior to when I updated IC and SC mask, 
% so I need to recreate them
tarray = timeExp;
ind1Mhz = round(1E6 / freqRes);
ws = round(10E3 / freqRes);
ICmask = freqVec.*0; SCmask = freqVec.*0;
ICmask(ind1Mhz*1.5+ws:2*ind1Mhz-ws)=1; % add 1.5 to 2 Mhz zone to IC
ICmask(ind1Mhz*2+ws:ind1Mhz*2.5-ws)=1; % add 2 to 2.5 zone to IC 
%SCmask(ind1Mhz-ws:ind1Mhz+ws)=1; % zero harmonic
SCmask(1.5*ind1Mhz-ws:1.5*ind1Mhz+ws)=1; % 1.5 harmonic
SCmask(2*ind1Mhz-ws:2*ind1Mhz+ws)=1; % 2 harmonic
SCmask(3*ind1Mhz-ws:3*ind1Mhz+ws)=1; % 3 harmonic
SCmask(0.5*ind1Mhz-ws:0.5*ind1Mhz+ws)=1; % 0.5 harmonic
SCmask(2.5*ind1Mhz-ws:2.5*ind1Mhz+ws)=1; % 2.5 harmonic

% compute IC and SC
scnew = zeros([dim(1) 1]);
icnew = zeros([dim(1) 1]);

for i=1:dim(1)
    scnew(i) = sum(Fsub(i,:).*SCmask);
    icnew(i) = sum(Fsub(i,:).*ICmask);
end

% divide by number of points in mask
scnew = scnew./sum(SCmask);
icnew = icnew./sum(ICmask);

% % remove any zeros
% scnew(scnew<=0)=.000001;
% icnew(icnew<=0)=.000001;
% 
% % log compress
% scnew = log10(scnew);
% icnew = log10(icnew);

dsf = 20;
scsmooth = movmean(scnew,dsf);
icsmooth = movmean(icnew,dsf);

% find plot limits that work
Sm = mean(scnew); Ss = std(scnew);
Im = mean(icnew); Is = std(icnew);
lim = [ min([Sm-3*Ss Im-3*Is]) max([Sm+3*Ss Im+3*Is])];

subplot(4,1,3)
plot(tarray,scnew,'color',[0.5 0.5 0.5],'lineStyle','--')
hold on
plot(tarray,scsmooth,'linewidth',1.5,'color',[0.5 0.5 0.5])
plot(tarray,icnew,'color',[0.2 0.2 0.2],'lineStyle','--')
plot(tarray,icsmooth,'linewidth',1.5,'color',[0.2 0.2 0.2])
%legend('Stable cavitation','Stable cavitation average','Inertial cavitation','Inertial cavitation average')
ylabel('Cavitation signal (a.u.)');
xlabel('time (s)')
xlim([0 tarray(end)])
ylim(lim)
set(gcf,'color','white')
%title(fn, 'Interpreter', 'none')



%% plot pressure used vs time

ampsUsedInt = str2num(data.ampsUsed);

% at 00-10
% MPaperAmp = 0.0761; % "A" value for 0,0,-10 steering
% MPaOffset = 0.1925; % "B" value

% at 000
MPaperAmp = .0672;
MPaOffset = .2223;

% put days with diff steering here:
if strcmp(fn, '021422_therapy2.mat')
    MPaperAmp = 0.0647; % "A" value for 0,0,-10 steering
    MPaOffset = 0.1456; % "B" value
end

pres = ampsUsedInt*MPaperAmp + MPaOffset;
Trans = .25; % estimated transmission

% % phantom transmission is 100%
% if strcmp(fn(1:2),'no')
%     Trans=1;
% end

pres = pres.*Trans;
tarray = (0:1:length(pres)-1)./prf;
%tarray = timeExp(1:length(pres));
subplot(4,1,4)
plot(tarray,pres,'linewidth',1,'color',[0 0 0])
xlabel('time (s)')
ylabel('Pressure [MPa]')
xlim([0 tarray(end)])
set(gcf,'color','white');
%title(fn, 'Interpreter', 'none')

end

    

