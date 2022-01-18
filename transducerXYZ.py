# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------------
# Copyright (C) Image Guided Therapy, Pessac, France - 2011. All Rights Reserved.
# This code is confidential and can not be copied or publicly released.
#---------------------------------------------------------------------------------


import math
try:  # for Python 2/3 compatibility
	from StringIO import StringIO
except ImportError:
	from io import StringIO
try:  # for Python 2/3 compatibility
	import ConfigParser as cfg
except ImportError:
	import configparser as cfg


SOUND_SPEED_WATER = 1500.0  # sound speed in water, m.s-1
TWO_PI = 2.0 * math.pi      # 2 pi, rad


class Transducer(object):
	"""
	A representation of the device used to shoot.
	It must be initialized from a definition file that contains basically the positions
	of its elements.
	Its working space is:
	- origin (0,0,0) at the natural focal point (all phases = 0)
	- Z axis toward the transducer
	"""
	def __init__ (self):
		#self.name = ""
		#self.focalLength = 0
		self.elements = []


	def load (self, filename):
		#config = cfg.ConfigParser()
		# this easy version can not be used because of the checksum trick
		# that raises a ConfigParser.MissingSectionHeaderError
		#if config.read (filename) == []:
		#    return False
		#return self._loadConfig (config)
		text = ""
		outside = True
		try:
			f = open (filename, "r")
			for line in f:
				if line.strip() == "": continue
				if outside:
					if line.strip()[0] == "[":
						text += line
						outside = False
					continue
				text += line
			return self.loadFromString (text)
		except IOError as e:
			print ("Error: "+str(e))
			return False

	def loadFromString (self, definition):
		config = cfg.ConfigParser()
		stringio = StringIO(definition)
		if config.readfp (stringio) == []:
			return False
		return self._loadConfig (config)


	def _loadConfig (self, config):
		size = 0
		#self.name = ""
		try:
			#self.name = config.get ("transducer", "name")
			#self.focalLength = config.getfloat ("transducer", "focalLength") / 1000.0
			size = config.getint ("elements", "size")
		except:
			return False
		if size == 0:
			return False
		
		self.elements = []
		for i in range(1,1+size):
			try:
				elem = config.get ("elements", "%d" % i).strip()
				coords = elem.split("|")
				# read coordinates in mm (convert them in m)
				item = (float(coords[0])/1000.0, float(coords[1])/1000.0, float(coords[2])/1000.0)
				self.elements.append (item)
			except:
				return False
		
		return True


	def channelCount (self):
		"""Returns the number of channels / elements."""
		return len(self.elements)


	def computePhases (self, shot, point_mm):
		"""
		Computes the phases necessary to aim at the specified point, and writes them directly in the given shot.
		shot: the shot to modify, its frequencies must be set before, its phases are modified (and resized)
		point_mm: a 3-tuple (x,y,z) = cartesian coordinates in mm, in the transducer space
		"""
		freqCount = shot.frequencyCount()
		if freqCount == 1:
			wavelen = SOUND_SPEED_WATER / shot.frequency(0)
		elif freqCount != self.channelCount():
			print ("Error: bad number of frequencies (%d in shot, %d channels in transducer)" % (freqCount, self.channelCount()))
			return False

		shot.resizePhases (self.channelCount(), False)
		x = point_mm[0] / 1000.0
		y = point_mm[1] / 1000.0
		z = point_mm[2] / 1000.0

		for i in range(len(self.elements)):
			elem = self.elements[i]
			if freqCount > 1:
				wavelen = SOUND_SPEED_WATER / shot.frequency(i)
			dist = math.sqrt (math.pow(elem[0]-x,2) + math.pow(elem[1]-y,2) + math.pow(elem[2]-z,2))
			rem = math.modf(dist / wavelen)[0]
			phase = int(0.5 + rem * 256.0)
			shot.setPhase (i, phase % 256)
		return True
