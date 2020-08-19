############################################################################
#             	Postprocessing tool

# Created by: 	Huy Pham
# 				University of California, Berkeley

# Date created:	August 2020

# Description: 	Script reads /outputs/ values and extract relevant maxima
#				Results are returned in a DataFrame row
#				Results are created and called using dictionaries

# Open issues: 	(1) avoid rerunning design script

############################################################################

import pandas as pd
import numpy as np
import math
import LHS

# functions to standardize csv output
def getShape(shape):
	shapeName 		= shape.iloc[0]['AISC_Manual_Label']
	return(shapeName)

# main function
def failurePostprocess(filename, defFactor, runStatus):

	# take input as the run 'ok' variable from eqAnly, passes that as one of the results csv columns

	# gather inputs
	bearingParams 			= pd.read_csv('./inputs/bearingInput.csv', index_col=None, header=0)

	# param is dictionary of all inputs. call with param['whatYouWant']
	param 					= dict(zip(bearingParams.variable, bearingParams.value))

	# create new dictionary for non-inputs. Put all tabulated results here.
	afterRun 				= dict()

	afterRun['GMFile'] 		= filename

	# redo scaling
	S1Actual 				= param['S1']*param['S1Ampli']
	S1Default 				= 1.017
	afterRun['GMScale'] 	= S1Actual/S1Default*defFactor

	# get selections and append to non-input dictionary
	import superStructDesign as sd
	(mu1, mu2, mu3, R1, R2, R3, moatGap, selectedBeam, selectedRoofBeam, selectedCol) = sd.design()

	fromDesign 		= {
		'mu1'		: mu1,
		'mu2'		: mu2,
		'mu3'		: mu3,
		'R1'		: R1,
		'R2'		: R2,
		'R3'		: R3,
		'beam'		: getShape(selectedBeam),
		'roofBeam'	: getShape(selectedRoofBeam),
		'col'		: getShape(selectedCol),
		'moatGap'	: float(moatGap),
	}

	afterRun.update(fromDesign)

	# gather outputs
	dispColumns = ['time', 'isol1', 'isol2', 'isol3', 'isol4', 'isolLC']

	isolDisp = pd.read_csv('./outputs/isolDisp.csv', sep=' ', header=None, names=dispColumns)
	isolVert = pd.read_csv('./outputs/isolVert.csv', sep=' ', header=None, names=dispColumns)
	isolRot  = pd.read_csv('./outputs/isolRot.csv', sep=' ', header=None, names=dispColumns)

	story1Disp = pd.read_csv('./outputs/story1Disp.csv', sep=' ', header=None, names=dispColumns)
	story2Disp = pd.read_csv('./outputs/story2Disp.csv', sep=' ', header=None, names=dispColumns)
	story3Disp = pd.read_csv('./outputs/story3Disp.csv', sep=' ', header=None, names=dispColumns)

	forceColumns = ['time', 'iAxial', 'iShearX', 'iShearY', 'iMomentX', 'iMomentY', 'iMomentZ', 'jAxial', 'jShearX', 'jShearY', 'jMomentX', 'jMomentY', 'jMomentZ']

	isol1Force = pd.read_csv('./outputs/isol1Force.csv', sep = ' ', header=None, names=forceColumns)
	isol2Force = pd.read_csv('./outputs/isol2Force.csv', sep = ' ', header=None, names=forceColumns)
	isol3Force = pd.read_csv('./outputs/isol3Force.csv', sep = ' ', header=None, names=forceColumns)
	isol4Force = pd.read_csv('./outputs/isol4Force.csv', sep = ' ', header=None, names=forceColumns)

	# maximum displacements across all isolators
	isol1Disp 		= abs(isolDisp['isol1'])
	isol2Disp 		= abs(isolDisp['isol2'])
	isol3Disp 		= abs(isolDisp['isol3'])
	isol4Disp 		= abs(isolDisp['isol4'])
	isolMaxDisp 	= np.maximum.reduce([isol1Disp, isol2Disp, isol3Disp, isol4Disp])

	afterRun['maxDisplacement'] 	= max(isolMaxDisp) 					# max recorded displacement over time

	# normalized shear in isolators
	force1Normalize = -isol1Force['iShearX']/isol1Force['iAxial']
	force2Normalize = -isol2Force['iShearX']/isol2Force['iAxial']
	force3Normalize = -isol3Force['iShearX']/isol3Force['iAxial']
	force4Normalize = -isol4Force['iShearX']/isol4Force['iAxial']

	# drift ratios recorded
	ft 				= 12
	story1DriftOuter 	= (story1Disp['isol1'] - isolDisp['isol1'])/(13*ft)
	story1DriftInner 	= (story1Disp['isol2'] - isolDisp['isol2'])/(13*ft)

	story2DriftOuter 	= (story2Disp['isol1'] - story1Disp['isol1'])/(13*ft)
	story2DriftInner 	= (story2Disp['isol2'] - story1Disp['isol2'])/(13*ft)

	story3DriftOuter 	= (story3Disp['isol1'] - story2Disp['isol1'])/(13*ft)
	story3DriftInner 	= (story3Disp['isol2'] - story2Disp['isol2'])/(13*ft)

	# drift failure check
	driftLimit 			= 0.05

	afterRun['driftMax1']	= max(np.maximum(story1DriftOuter, story1DriftInner))
	afterRun['driftMax2']	= max(np.maximum(story2DriftOuter, story2DriftInner))
	afterRun['driftMax3']	= max(np.maximum(story3DriftOuter, story3DriftInner))

	afterRun['drift1']	= 0
	afterRun['drift2'] 	= 0
	afterRun['drift3'] 	= 0

	if(any(abs(driftRatio) > driftLimit for driftRatio in story1DriftOuter) or any(abs(driftRatio) > driftLimit for driftRatio in story1DriftInner)):
		afterRun['drift1'] 	= 1

	if(any(abs(driftRatio) > driftLimit for driftRatio in story2DriftOuter) or any(abs(driftRatio) > driftLimit for driftRatio in story2DriftInner)):
		afterRun['drift2'] 	= 1

	if(any(abs(driftRatio) > driftLimit for driftRatio in story3DriftOuter) or any(abs(driftRatio) > driftLimit for driftRatio in story3DriftInner)):
		afterRun['drift3'] 	= 1

	# impact check
	moatGap 				= float(moatGap)
	afterRun['impacted'] 	= 0

	if(any(displacement >= moatGap for displacement in isolMaxDisp)):
		afterRun['impacted'] 	= 1

	# uplift check
	minFv 					= 5.0			# kips
	afterRun['uplifted'] 	= 0

	# isolator axial forces
	isol1Axial 		= abs(isol1Force['iAxial'])
	isol2Axial 		= abs(isol2Force['iAxial'])
	isol3Axial 		= abs(isol3Force['iAxial'])
	isol4Axial 		= abs(isol4Force['iAxial'])

	isolMinAxial 	= np.minimum.reduce([isol1Axial, isol2Axial, isol3Axial, isol4Axial])

	if(any(axialForce <= minFv for axialForce in isolMinAxial)):
		afterRun['uplifted'] 	= 1

	# use run status passed in
	afterRun['runFailed'] 	= runStatus

	# merge input and output dictionaries, then output as dataframe
	runDict 		= {**param, **afterRun}
	runRecord 		= pd.DataFrame.from_dict(runDict, 'index').transpose()			# 'index' puts keys as index column. transpose so results are in a row.
	runHeader 		= list(runRecord.columns)										# pass column names to runControl
	
	return(runHeader, runRecord)

if __name__ == '__main__':
	thisHeader, thisRun 		= failurePostprocess('testfilename', 3.0, 0)
	print(thisRun)