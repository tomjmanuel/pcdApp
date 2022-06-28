% Calculates the amplitude interger to be used given a steering coordinate
% [X, Y, Z] (in mm) and requested pressure (in MPa). Steering needs to be less than in all
% directions. Requires having the IGTCalibrationFit.mat file in the path.
% Data was collected on 20220111 by MAP and TJM. 


function [integerAmplitude] = getAtacAmpInt(steeringCoord, pressureOutput)

% This calibration data are the linear fit coefficents up to a MI limit 4.5
% for a grid of data [0, 0:5:15, -15:0:15. The data has been intepolated
% with interp2 and spline up to 0.1mm step size. 
load('ATACCalibrationFit.mat'); 

% convert the data to radial and axial distances to map to the 2D plane of
% data loaded above
radialSteer = round(sqrt(steeringCoord(1)^2 + steeringCoord(2)^2),1);
axialSteer = round(steeringCoord(3),1);

if radialSteer > 15 || axialSteer > 15 || axialSteer < -20
    error('Error. Too large of a steering Value')
end

% Rescale to match 0.1mm step size
radialSteer = radialSteer*10;
axialSteer = axialSteer*10;

% Shift to be matlab position based
radialSteerShift = radialSteer+1;
axialSteerShift = axialSteer+200+1;

% calculate tha value
integerAmplitude = round((pressureOutput-BfitInterp(radialSteerShift,axialSteerShift))/ ... 
    AfitInterp(radialSteerShift,axialSteerShift));

end