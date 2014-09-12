from __future__ import division

from lenstools.external import _gadget

import numpy as np
from astropy.units import kpc,Mpc,cm,km,g,s,Msun

try:
	
	import matplotlib.pyplot as plt
	from mpl_toolkits.mplot3d import Axes3D
	matplotlib = True

except ImportError:

	matplotlib = False

############################################################
################Gadget2Header class#########################
############################################################

class Gadget2Header(dict):

	"""
	Class handler of a Gadget2 snapshot header

	"""

	def __init__(self,HeaderDict=dict()):

		super(Gadget2Header,self).__init__()
		for key in HeaderDict.keys():
			self[key] = HeaderDict[key]

	def __repr__(self):

		keys = self.keys()
		keys.sort()
		
		return "\n".join([ "{0} : {1}".format(key,self[key]) for key in keys ]) 

	def __add__(self,rhs):

		assert isinstance(rhs,Gadget2Header),"addition not defined if rhs is not a Gadget2Header!"

		#Check that it makes sense to add the snapshots (cosmological parameters, box size, time and redshift must agree)
		fields_to_match = ["Ode0","Om0","h","box_size","endianness","flag_cooling","flag_feedback","flag_sfr","num_files"]
		fields_to_match += ["num_particles_total","num_particles_total_gas","num_particles_total_side","num_particles_total_with_mass","redshift","scale_factor"]

		for field in fields_to_match:
			assert self[field] == rhs[field],"{0} fields do not match!".format(field)

		assert np.all(self["masses"]==rhs["masses"])
		assert np.all(self["num_particles_total_of_type"]==rhs["num_particles_total_of_type"])

		#Construct the header of the merged snapshot
		merged_header = self.copy()
		merged_header["files"] += rhs["files"]
		merged_header["num_particles_file"] += rhs["num_particles_file"]
		merged_header["num_particles_file_gas"] += rhs["num_particles_file_gas"]
		merged_header["num_particles_file_of_type"] += rhs["num_particles_file_of_type"]
		merged_header["num_particles_file_with_mass"] += rhs["num_particles_file_with_mass"]

		return merged_header

############################################################
#################Gadget2Snapshot class######################
############################################################

class Gadget2Snapshot(object):

	"""
	A class that handles I/O from Gadget2 snapshots: it was mainly designed to parse physical information from binary gadget snapshots

	"""

	def __init__(self,fp=None):

		assert (type(fp)==file) or (fp is None),"Call the open() method instead!!"

		if fp is not None:
		
			self.fp = fp
			self._header = Gadget2Header(_gadget.getHeader(fp))
			self._header["files"] = [self.fp.name]

			#Scale box to kpc
			self._header["box_size"] *= kpc
			#Convert to Mpc
			self._header["box_size"] = self._header["box_size"].to(Mpc)

			#Scale masses to correct units
			self._header["masses"] *= (1.989e43 / self._header["h"])
			self._header["masses"] *= g
			self._header["masses"] = self._header["masses"].to(Msun) 

			#Scale Hubble parameter to correct units
			self._header["H0"] = self._header["h"] * 100 * km / (s*Mpc)

			#Update the dictionary with the number of particles per side
			self._header["num_particles_total_side"] = int(np.round(self._header["num_particles_total"]**(1/3)))

	@classmethod
	def open(cls,filename):

		"""
		Opens a gadget snapshot at filename

		:param filename: file name of the gadget snapshot
		:type filename: str. or file.
		"""

		if type(filename)==str:
			fp = open(filename,"r")
		elif type(filename)==file:
			fp = filename
		else:
			raise TypeError("filename must be string or file!")
		
		return cls(fp)

	@property
	def header(self):

		"""
		Displays the snapshot header information

		:returns: the snapshot header information in dictionary form
		:rtype: dict.

		"""

		return self._header

	def getPositions(self,first=None,last=None):

		"""
		Reads in the particles positions (read in of a subset is allowed): when first and last are specified, the numpy array convention is followed (i.e. getPositions(first=a,last=b)=getPositions()[a:b])

		:param first: first particle in the file to be read, if None 0 is assumed
		:type first: int. or None

		:param last: last particle in the file to be read, if None the total number of particles is assumed
		:type last: int. or None

		:returns: numpy array with the particle positions

		"""

		assert not self.fp.closed

		numPart = self._header["num_particles_file"]

		#Calculate the offset from the beginning of the file: 4 bytes (endianness) + 256 bytes (header) + 8 bytes (void)
		offset = 4 + 256 + 8

		#If first is specified, offset the file pointer by that amount
		if first is not None:
			
			assert first>=0
			offset += 4 * 3 * first
			numPart -= first

		if last is not None:

			if first is not None:
				
				assert last>=first and last<=self._header["num_particles_file"]
				numPart = last - first

			else:

				assert last<=self._header["num_particles_file"]
				numPart = last


		#Read in the particles positions and return the corresponding array
		self.positions = (_gadget.getPosVel(self.fp,offset,numPart) * kpc).to(Mpc) 
		
		#Return
		return self.positions

	def getVelocities(self,first=None,last=None):

		"""
		Reads in the particles velocities (read in of a subset is allowed): when first and last are specified, the numpy array convention is followed (i.e. getVelocities(first=a,last=b)=getVelocities()[a:b])

		:param first: first particle in the file to be read, if None 0 is assumed
		:type first: int. or None

		:param last: last particle in the file to be read, if None the total number of particles is assumed
		:type last: int. or None

		:returns: numpy array with the particle velocities

		"""

		assert not self.fp.closed

		numPart = self._header["num_particles_file"]

		#Calculate the offset from the beginning of the file: 4 bytes (endianness) + 256 bytes (header) + 8 bytes (void)
		offset = 4 + 256 + 8

		#Skip all the particle positions
		offset += 4 * 3 * numPart

		#Skip other 8 void bytes
		offset += 8

		#If first is specified, offset the file pointer by that amount
		if first is not None:
			
			assert first>=0
			offset += 4 * 3 * first
			numPart -= first

		if last is not None:

			if first is not None:
				
				assert last>=first and last<=self._header["num_particles_file"]
				numPart = last - first

			else:

				assert last<=self._header["num_particles_file"]
				numPart = last


		#Read in the particles positions and return the corresponding array
		self.velocities = _gadget.getPosVel(self.fp,offset,numPart)

		#Scale units
		self.velocities *= 1.0e5
		self.velocities *= cm / s
		
		#Return
		return self.velocities

	def getID(self,first=None,last=None):

		"""
		Reads in the particles IDs, 4 byte ints, (read in of a subset is allowed): when first and last are specified, the numpy array convention is followed (i.e. getID(first=a,last=b)=getID()[a:b])

		:param first: first particle in the file to be read, if None 0 is assumed
		:type first: int. or None

		:param last: last particle in the file to be read, if None the total number of particles is assumed
		:type last: int. or None

		:returns: numpy array with the particle IDs

		"""

		assert not self.fp.closed

		numPart = self._header["num_particles_file"]

		#Calculate the offset from the beginning of the file: 4 bytes (endianness) + 256 bytes (header) + 8 bytes (void)
		offset = 4 + 256 + 8

		#Skip all the particle positions
		offset += 4 * 3 * numPart

		#Skip other 8 void bytes
		offset += 8

		#Skip all the particle velocities
		offset += 4 * 3 * numPart

		#Skip other 8 void bytes
		offset += 8

		#If first is specified, offset the file pointer by that amount
		if first is not None:
			
			assert first>=0
			offset += 4 * first
			numPart -= first

		if last is not None:

			if first is not None:
				
				assert last>=first and last<=self._header["num_particles_file"]
				numPart = last - first

			else:

				assert last<=self._header["num_particles_file"]
				numPart = last


		#Read in the particles positions and return the corresponding array
		self.id = _gadget.getID(self.fp,offset,numPart)
		
		#Return
		return self.id


	def reorder(self):

		"""
		Sort particles attributes according to their ID

		"""

		assert hasattr(self,"id")

		#Sort positions
		if hasattr(self,"positions"):
			
			assert self.positions.shape[0]==len(self.id)
			self.positions = self.positions[self.id - 1]

		#Sort velocities
		if hasattr(self,"velocities"):

			assert self.velocities.shape[0]==len(self.id)
			self.velocities = self.velocities[self.id - 1]

		#Finally sort IDs
		self.id.sort() 


	def visualize(self,fig=None,ax=None,**kwargs):

		"""
		Visualize the particles in the Gadget snapshot using the matplotlib 3D plotting engine, the kwargs are passed to the matplotlib scatter method

		"""

		if not matplotlib:
			raise ImportError("matplotlib is not installed, cannot visualize!")

		#Get the positions if you didn't do it before
		if not hasattr(self,"positions"):
			self.getPositions()

		#Instantiate figure
		if (fig is None) or (ax is None):
			
			self.fig = plt.figure()
			self.ax = self.fig.add_subplot(111,projection="3d")

		else:

			self.fig = fig
			self.ax = ax

		#Put the particles in the figure
		self.ax.scatter(*self.positions.transpose(),**kwargs)

		#Put the labels on the axes
		self.ax.set_xlabel(r"$x({0})$".format(self.positions.unit.to_string()))
		self.ax.set_ylabel(r"$y({0})$".format(self.positions.unit.to_string()))
		self.ax.set_zlabel(r"$z({0})$".format(self.positions.unit.to_string()))

	def savefig(self,filename):

		"""
		Save the snapshot visualization to an external file

		:param filename: file name to which the figure will be saved
		:type filename: str.

		"""

		self.fig.savefig(filename)

	def close(self):

		"""
		Closes the snapshot file

		"""

		self.fp.close()

	def write(self,filename):

		"""
		Writes particles information (positions, velocities, etc...) to a properly formatter Gadget snapshot

		:param filename: name of the file to which to write the snapshot
		:type filename: str.

		"""

		#Sanity checks
		assert hasattr(self,"positions") and hasattr(self,"velocities"),"Positions and velocities must be specified!!"
		assert self.positions.shape[0]==self.velocities.shape[0]

		if not hasattr(self,"_header"):
			self.setHeaderInfo()	

		#Build a bare header based on the available info (need to convert units back to the Gadget ones)
		_header_bare = self._header.copy()
		_header_bare["box_size"] = _header_bare["box_size"].to(kpc).value
		_header_bare["masses"] = _header_bare["masses"].to(g).value * _header_bare["h"] / 1.989e43
		_header_bare["num_particles_file_of_type"] = _header_bare["num_particles_file_of_type"].astype(np.int32)
		_header_bare["num_particles_total_of_type"] = _header_bare["num_particles_file_of_type"].astype(np.int32)

		#Convert units for positions and velocities
		_positions_converted = self.positions.to(kpc).value.astype(np.float32)
		_velocities_converted = (self.velocities.to(cm/s).value / 1.0e5).astype(np.float32)

		#Write it!!
		_gadget.write(_header_bare,_positions_converted,_velocities_converted,1,filename)

	
	def setPositions(self,positions):

		"""
		Sets the positions in the current snapshot (with the intent of writing them to a properly formatted snapshot file)

		:param positions: positions of the particles, must have units
		:type positions: (N,3) array with units

		"""

		assert positions.shape[1]==3
		assert positions.unit.physical_type=="length"

		self.positions = positions

	def setVelocities(self,velocities):

		"""
		Sets the velocities in the current snapshot (with the intent of writing them to a properly formatted snapshot file)

		:param velocities: velocities of the particles, must have units
		:type velocities: (N,3) array with units

		"""

		assert velocities.shape[1]==3
		assert positions.unit.physical_type=="speed"

		self.velocities = velocities

	
	def setHeaderInfo(self,Om0=0.26,Ode0=0.74,h=0.72,redshift=1.0,box_size=15.0*Mpc,flag_cooling=0,flag_sfr=0,flag_feedback=0,masses=np.array([0,1.03e10,0,0,0,0])*Msun,num_particles_file_of_type=None):

		"""
		Sets the header info in the snapshot to write

		"""

		if num_particles_file_of_type is None:
			num_particles_file_of_type = np.array([0,1,0,0,0,0],dtype=np.int32) * self.positions.shape[0]

		assert num_particles_file_of_type.sum()==self.positions.shape[0],"The total number of particles must match!!"
		assert box_size.unit.physical_type=="length"
		assert masses.unit.physical_type=="mass"

		#Create the header
		self._header = Gadget2Header()
		
		#Fill in
		self._header["Om0"] = Om0
		self._header["Ode0"] = Ode0
		self._header["h"] = h
		self._header["redshift"] = redshift
		self._header["scale_factor"] = 1.0 / (1.0 + redshift)
		self._header["box_size"] = box_size
		self._header["flag_cooling"] = flag_cooling
		self._header["flag_sfr"] = flag_sfr
		self._header["flag_feedback"] = flag_feedback
		self._header["masses"] = masses
		self._header["num_particles_file_of_type"] = num_particles_file_of_type
		self._header["num_particles_file"] = num_particles_file_of_type.sum()
		self._header["num_particles_total_of_type"] = num_particles_file_of_type
		self._header["num_particles_total"] = num_particles_file_of_type.sum()


	def __add__(self,rhs):

		"""
		Add two gadget snapshots together: useful when the particle content is split between different files; all the positions and particle velocities are vstacked together

		"""

		merged_snapshot = Gadget2Snapshot(None)
		merged_snapshot._header = self._header + rhs._header

		if hasattr(self,"positions") and hasattr(rhs,"positions"):
			
			assert self.positions.unit==rhs.positions.unit
			merged_snapshot.positions = np.vstack((self.positions.value,rhs.positions.value))
			merged_snapshot.positions *= self.positions.unit

		if hasattr(self,"velocities") and hasattr(rhs,"velocities"):
			
			assert self.velocities.unit==rhs.velocities.unit
			merged_snapshot.velocities = np.vstack((self.velocities.value,rhs.velocities.value))
			merged_snapshot.velocities *= self.velocities.unit

		if hasattr(self,"id") and hasattr(rhs,"id"):

			merged_snapshot.id = np.hstack((self.id,rhs.id))


		return merged_snapshot



