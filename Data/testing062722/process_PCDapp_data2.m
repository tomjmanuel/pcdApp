%% Tom 03/16/22
% This script takes the raw therapy data and processes it entirely in matlab
% Rather than just plot what I have saved, I am trying to double check
% this datas processing as it will likely be published

fn = 'data13.mat'; % higher pressure at first then dropped down
%fn = 'try2_bubs.mat'; %
load(fn);
prf = str2num(prf);
%% 
% the baselines are already fft and averaged but not log
% we have one baseline for every amp
% looks like we didn't save the range of amps, need to add that to
% pcdApp code
% looking at 02/14/22 notes it was: 
% amp val: 29 	39 	49 	59 	69 	79 	89
% MPa ff:  2.4	3.1	3.9	4.6	5.4	6.2	7

% convert ampsUsed to numbers
ampsUsedInt = str2num(ampsUsed);

% SpectData is already fft and log compressed and subtracted actually
% we can just use that at first
% the freqAxis variable holds the frequency axis out to the relevant
% frequencies

% make the spectrogram image
nfreqPts = length(freqAxis); % crop freq additionally 
%ntpts = length(ampsUsedInt);
ntpts = size(SpectData,2);
tarray = (0:ntpts-1)./prf; % time array in seconds
%Clim = [3.17 4.25]; % therapy 1contrast range (use imtool to find)
%Clim = [3.1 3.9]; % therapy 2
Clim = [2.5 5];
figure
imagesc(tarray,freqAxis(1:nfreqPts),SpectData(1:nfreqPts,1:ntpts),Clim);
colormap('gray')
xlabel('time (s)')
ylabel('MHz')
set(gcf,'color','white')

%% receate SC and IC mask (skip if on data collected after 021422
% now make the IC and SC plots
% this data was collected prior to when I updated IC and SC mask, 
% so I need to recreate them
ind1Mhz = 501;
ws = 10;
ICmask = ICmask.*0; SCmask = SCmask.*0;
ICmask(ind1Mhz+ws:2*ind1Mhz-ws)=1; % add 1 to 2 Mhz zone
ICmask(ind1Mhz*1.5-ws:ind1Mhz*1.5+ws)=0; % remove 1.5 harmonic 
SCmask(ind1Mhz-ws:ind1Mhz+ws)=1; % first harmonic
SCmask(1.5*ind1Mhz-ws:1.5*ind1Mhz+ws)=1; % 1.5 harmonic
SCmask(2*ind1Mhz-ws:2*ind1Mhz+ws)=1; % 2 harmonic
SCmask(3*ind1Mhz-ws:3*ind1Mhz+ws)=1; % 3 harmonic
SCmask(0.5*ind1Mhz-ws:0.5*ind1Mhz+ws)=1; % 0.5 harmonic
SCmask(2.5*ind1Mhz-ws:2.5*ind1Mhz+ws)=1; % 0.5 harmonic
% compute IC and SC
scnew = zeros([ntpts 1]);
icnew = zeros([ntpts 1]);
for i=1:ntpts
    scnew(i) = sum(SpectData(1:length(freqAxis),i).*SCmask);
    icnew(i) = sum(SpectData(1:length(freqAxis),i).*ICmask);
end

% subtract off starting values (prebubble)
scnew = scnew-mean(scnew(1:10));
icnew = icnew-mean(icnew(1:10));

% divide by number of points in mask
scnew = scnew./sum(SCmask);
icnew = icnew./sum(ICmask);

% % scale a.u. so SC goes up to 1
% sf = max(scnew(:)); % scale factor
% scnew = scnew.*(1/sf);
% icnew = icnew.*(1/sf);

% compute runnign average to also overlay
% dsf=10;
% tds = tarray(1:dsf:end);
% scds = interp1(tarray,scnew,tds);
% icds = interp1(tarray,icnew,tds);
dsf = 20;
scsmooth = movmean(scnew,dsf);
icsmooth = movmean(icnew,dsf);

figure
plot(tarray,scnew,'color',[0.5 0.5 0.5],'lineStyle','--')
hold on
plot(tarray,scsmooth,'linewidth',2,'color',[0.5 0.5 0.5])
plot(tarray,icnew,'color',[0.2 0.2 0.2],'lineStyle','--')
plot(tarray,icsmooth,'linewidth',2,'color',[0.2 0.2 0.2])
legend('Stable cavitation','Stable cavitation average','Inertial cavitation','Inertial cavitation average')
ylabel('Cavitation signal (a.u.)');
xlabel('time (s)')
%ylim([-0.15 4])
xlim([0 tarray(end)])
set(gcf,'color','white')


%% plot pressure used vs time (therapy 1)
% amp val: 29 	39 	49 	59 	69 	79 	89
% MPa ff:  2.4	3.1	3.9	4.6	5.4	6.2	7

% fit vals for ATAC xdcr at 00-10
Afitn10 = .0761;
Bfitn10 = .1925; 

% pres = ampsUsedInt.*0;
% pres(ampsUsedInt==59)= 4.6*.15;
% pres(ampsUsedInt==49)= 3.9*.15;
% pres(ampsUsedInt==39)= 3.1*.15

pres = ampsUsedInt.*Afitn10 + Bfitn10;

figure
plot(tarray,pres(1:ntpts),'linewidth',1,'color',[0 0 0])
xlabel('time (s)')
ylabel('PNP MPa')
%ylim([0.4 0.8])
xlim([0 tarray(end)])
set(gcf,'color','white');

