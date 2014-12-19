"""

.. module:: contours 
	:platform: Unix
	:synopsis: This module implements a confidence contour plotting engine


.. moduleauthor:: Andrea Petri <apetri@phys.columbia.edu>


"""

from __future__ import print_function,division,with_statement

import os
import logging


import numpy as np
from scipy import stats
from scipy import integrate
import matplotlib.pyplot as plt
from matplotlib import rc

#############################################################
############Find likelihood levels in 1D likelihood##########
#############################################################

def _1d_level_values(p,l,level=0.684,quantity=2):

	"""
	Find the parameter extremes that correspons to the likelihood N--sigma level

	"""

	#Find the maximum of the likelihood
	maximum = np.where(l==l.max())[0][0]
	parmax = p[maximum]

	all_levels = np.zeros_like(l)
	
	for n in range(l.shape[0]):
		all_levels[n] = l[l>=l[n]].sum() / l.sum()

	#Find the closest level
	closest = np.argmin(np.abs(all_levels - level))

	#Find the n corresponding parameter values
	ranks = stats.rankdata(np.abs(l-l[closest])).astype(np.int) - 1

	par = list()
	for n in range(quantity):
		par.append(p[np.where(ranks==n)[0][0]])

	#Sort parameters in order of closeness to the maximum
	def _closest(x):
		return np.abs(x-parmax)

	par.sort(key=_closest)

	return par


#############################################################
##################ContourPlot class##########################
#############################################################

class ContourPlot(object):

	"""
	A class handler for contour plots

	"""

	def __init__(self,fig=None,ax=None):

		try:
			
			if (fig is None) or (ax is None):
				self.fig,self.ax = plt.subplots()
				self.ax.proxy = list()
			else:
				self.fig = fig
				self.ax = ax

				if not hasattr(self.ax,"proxy"):
					self.ax.proxy = list()

		except:

			print("Warning, no matplotlib functionalities!")
			pass
		
		self.min = dict()
		self.max = dict()
		self.npoints = dict()
		self.unit = dict()

	def savefig(self,figname):

		"""
		Save the plot to file

		"""

		self.fig.savefig(figname)


	def close(self):

		"""
		Closes the figure

		"""

		plt.close(self.fig)

	def getUnitsFromOptions(self,options):
		
		"""
		Parse options file to get physical units of axes

		"""

		assert hasattr(self,"parameter_axes"),"You have to load in the likelihood first!"
		parameters = self.parameter_axes.keys()

		for parameter in parameters:
			
			self.min[parameter],self.max[parameter],self.npoints[parameter] = options.getfloat(parameter,"min"),options.getfloat(parameter,"max"),options.getint(parameter,"num_points")
			assert self.npoints[parameter] == self.likelihood.shape[self.parameter_axes[parameter]]
			self.unit[parameter] = (self.max[parameter] - self.min[parameter]) / (self.npoints[parameter] - 1)

	def setUnits(self,parameter,parameter_min,parameter_max,parameter_unit):

		"""
		Set manually the physical units for each of the likelihood axes

		"""
		assert hasattr(self,"parameter_axes"),"You have to load in the likelihood first!"
		assert parameter in self.parameter_axes.keys(),"You are trying to set units for a parameter that doesn't exist!"

		self.min[parameter] = parameter_min
		self.max[parameter] = parameter_max
		self.unit[parameter] = parameter_unit

		print("Units set for {0}; min={1:.3f} max={2:.3f} unit={3:.3f}".format(parameter,parameter_min,parameter_max,parameter_unit))

	def value(self,*coordinates):

		"""
		Compute the (un-normalized) likelihood value at the specified point in parameter space

		"""

		assert len(coordinates) == self.likelihood.ndim,"You must specify a coordinate (and only one) for each axis"

		#Compute the physical values of the pixels
		pix = np.zeros(len(coordinates))
		for parameter in self.parameter_axes.keys():

			assert parameter in self.unit.keys() and parameter in self.min.keys()
			axis = self.parameter_axes[parameter]
			pix[axis] = int((coordinates[axis] - self.min[parameter])/(self.unit[parameter]))

		#Return the found likelihood value
		try:
			return self.likelihood[tuple(pix)]
		except IndexError:
			print("Out of bounds!")
			return None


	def getLikelihood(self,likelihood_filename,parameter_axes={"Omega_m":0,"w":1,"sigma8":2},parameter_labels={"Omega_m":r"$\Omega_m$","w":r"$w$","sigma8":r"$\sigma_8$"}):
		
		"""
		Load the likelihood function from a numpy file

		"""

		self.parameter_axes = parameter_axes
		self.parameter_labels = parameter_labels

		if type(likelihood_filename)==str:
			
			self.likelihood = np.load(likelihood_filename)
			#Construct title label
			self.title_label = os.path.split(likelihood_filename)[1].lstrip("likelihood_").rstrip(".npy")
		
		elif type(likelihood_filename)==np.ndarray:
			
			self.likelihood = likelihood_filename
			#Construct title label
			self.title_label = "Default"

		assert len(self.parameter_axes.keys()) == self.likelihood.ndim,"The number of parameters should be the same as the number of dimensions of the likelihood!"

	def getMaximum(self,which="full"):

		"""
		Find the point in parameter space on which the likelihood is maximum

		"""
		max_parameters = dict()

		if which=="full":
			
			max_loc = np.where(self.likelihood==self.likelihood.max())
			for parameter in self.parameter_axes.keys():
				max_parameters[parameter] = max_loc[self.parameter_axes[parameter]][0] * self.unit[parameter] + self.min[parameter]
		
		elif which=="reduced":
			
			max_loc = np.where(self.reduced_likelihood==self.reduced_likelihood.max())
			for n,parameter in enumerate(self.remaining_parameters):
				max_parameters[parameter] = max_loc[n][0] * self.unit[parameter] + self.min[parameter]
		
		else:
			raise ValueError("which must be either 'full' or 'reduced'")

		return max_parameters


	def expectationValue(self,function,**kwargs):

		"""
		Computes the expectation value of a function of the parameters over the current parameter likelihood

		"""

		assert hasattr(self,"likelihood"),"You have to load in the likelihood first!"

		#Parameters
		parameters = self.parameter_axes.keys()
		parameters.sort(key=self.parameter_axes.__getitem__)

		#Initialize the parameter mesh
		mesh_axes = [ np.linspace(self.min[par],self.max[par],self.npoints[par]) for par in parameters ]
		parameter_mesh = np.meshgrid(*tuple(mesh_axes),indexing="ij")

		#Compute the expectation value
		expectation = (function(parameter_mesh,**kwargs)*self.likelihood).sum() / self.likelihood.sum()  

		#Return
		return expectation


	def variance(self,function,**kwargs):

		"""
		Computes the variance of a function of the parameters over the current parameter likelihood

		"""

		expectation = self.expectationValue(function,**kwargs)

		#Parameters
		parameters = self.parameter_axes.keys()
		parameters.sort(key=self.parameter_axes.__getitem__)

		#Initialize the parameter mesh
		mesh_axes = [ np.linspace(self.min[par],self.max[par],self.npoints[par]) for par in parameters ]
		parameter_mesh = np.meshgrid(*tuple(mesh_axes),indexing="ij")

		#Compute the variance
		variance = (self.likelihood*(function(parameter_mesh,**kwargs) - expectation)**2).sum() / self.likelihood.sum()

		#Return 
		return variance


	def marginalize(self,parameter_name="w"):

		"""
		Marginalize the likelihood over one of the parameters

		"""

		assert hasattr(self,"likelihood"),"You have to load in the likelihood first!"
		assert parameter_name in self.parameter_axes.keys(),"You are trying to marginalize over a parameter that does not exist!"
		
		if self.likelihood.ndim<3:
			
			print("The likelihood is already marginal!")
			self.reduced_likelihood = self.likelihood / self.likelihood.sum()
			self.remaining_parameters = self.parameter_axes.keys()

		else:

			self.reduced_likelihood = self.likelihood.sum(self.parameter_axes[parameter_name])

			#Normalize
			self.reduced_likelihood /= self.reduced_likelihood.sum()

			#Find the remaining parameters
			self.remaining_parameters = self.parameter_axes.keys()
			self.remaining_parameters.pop(self.remaining_parameters.index(parameter_name))
			#Sort the remaining parameter names so that the corresponding axes are in increasing order
			self.remaining_parameters.sort(key=self.parameter_axes.get)
		
		self.extent = (self.min[self.remaining_parameters[0]],self.max[self.remaining_parameters[0]],self.min[self.remaining_parameters[1]],self.max[self.remaining_parameters[1]])
		self.ax.set_xlim(self.extent[0],self.extent[1])
		self.ax.set_ylim(self.extent[2],self.extent[3])


	def marginal(self,parameter_name="w",levels=None):

		"""
		Marginalize the likelihood over all parameters but one

		"""

		assert hasattr(self,"likelihood"),"You have to load in the likelihood first!"
		assert parameter_name in self.parameter_axes.keys(),"You are trying to compute a marginal likelihood of a parameter that does not exist!"

		remaining_parameters = self.parameter_axes.keys()
		remaining_parameters.pop(remaining_parameters.index(parameter_name))
		remaining_parameter_axes = [ self.parameter_axes[par] for par in remaining_parameters ]

		#Marginalize the likelihood
		parameter_range = np.linspace(self.min[parameter_name],self.max[parameter_name],self.npoints[parameter_name])
		marginal_likelihood = self.likelihood.sum(axis=tuple(remaining_parameter_axes))

		#Compute the normalization
		normalization = integrate.simps(marginal_likelihood,x=parameter_range)
		marginal_likelihood /= normalization

		#Compute the maximum
		par_max = parameter_range[np.where(marginal_likelihood==marginal_likelihood.max())[0][0]]

		#Compute also the contour extremes if levels 
		if levels is not None:

			par_extremes = list()
			for level in levels:

				pL = _1d_level_values(parameter_range,marginal_likelihood,level=level,quantity=3)
				par_extremes.append((pL[0],pL[1]))

			#Return the normalized single parameter likelihood, along with the contour extremes
			return parameter_range,marginal_likelihood,par_max,par_extremes

		else:
			
			#Return the normalized single parameter likelihood
			return parameter_range,marginal_likelihood,par_max


	def slice(self,parameter_name="w",parameter_value=-1.0):

		"""
		Slice the likelihood cube by fixing one of the parameters

		"""

		assert hasattr(self,"likelihood"),"You have to load in the likelihood first!"
		assert parameter_name in self.parameter_axes.keys(),"You are trying to get a slice with a parameter that does not exist!"
		
		if self.likelihood.ndim<3:
			
			print("The likelihood is already sliced!")
			self.reduced_likelihood = self.likelihood / self.likelihood.sum()
			self.remaining_parameters = self.parameter_axes.keys()

		else:
			
			#Select the slice
			slice_axis = self.parameter_axes[parameter_name]
			slice_index = int((parameter_value - self.min[parameter_name]) / self.unit[parameter_name])
			assert slice_index<self.npoints[parameter_name],"Out of bounds!"

			#Get the slice
			self.reduced_likelihood = np.split(self.likelihood,self.npoints[parameter_name],axis=slice_axis)[slice_index].squeeze()
			
			#Normalize
			self.reduced_likelihood /= self.reduced_likelihood.sum()

			#Find the remaining parameters
			self.remaining_parameters = self.parameter_axes.keys()
			self.remaining_parameters.pop(self.remaining_parameters.index(parameter_name))
			#Sort the remaining parameter names so that the corresponding axes are in increasing order
			self.remaining_parameters.sort(key=self.parameter_axes.get)
		
		self.extent = (self.min[self.remaining_parameters[0]],self.max[self.remaining_parameters[0]],self.min[self.remaining_parameters[1]],self.max[self.remaining_parameters[1]])
		self.ax.set_xlim(self.extent[0],self.extent[1])
		self.ax.set_ylim(self.extent[2],self.extent[3])


	def show(self):

		"""
		Show the 2D marginalized likelihood

		"""

		assert self.reduced_likelihood.ndim == 2,"The marginalized likelihood must be two dimensional!!"
		
		self.likelihood_image = self.ax.imshow(self.reduced_likelihood.transpose(),origin="lower",cmap=plt.cm.binary_r,extent=self.extent,aspect="auto")
		self.colorbar = plt.colorbar(self.likelihood_image,ax=self.ax)
		

	def labels(self,contour_label=None,fontsize=22,**kwargs):

		"""
		Put the labels on the plot

		"""

		self.ax.set_xlabel(self.parameter_labels[self.remaining_parameters[0]],fontsize=fontsize)
		self.ax.set_ylabel(self.parameter_labels[self.remaining_parameters[1]],fontsize=fontsize)
		self.ax.set_title(self.title_label,fontsize=fontsize)

		if contour_label is not None:
			self.ax.legend(self.ax.proxy,contour_label,**kwargs)

	def point(self,coordinate_x,coordinate_y,color="green",marker="o"):

		"""
		Draws a point in parameter space at the specified physical coordinates

		"""

		#First translate the physical coordinates into pixels, to obtain the likelihood value
		px = int((coordinate_x - self.min[self.remaining_parameters[0]]) / self.unit[self.remaining_parameters[0]])
		py = int((coordinate_y - self.min[self.remaining_parameters[1]]) / self.unit[self.remaining_parameters[1]])

		#Draw the point
		self.ax.plot(coordinate_x,coordinate_y,color=color,marker=marker)

		#Return the likelihood value at the specified point
		return self.reduced_likelihood[px,py]


	#################################################################################################
	###############Find the likelihood values that correspond to the confidence contours#############
	#################################################################################################

	def getLikelihoodValues(self,levels,epsilon=0.01,max_iterations=1000):

		"""
		Find the likelihood values that correspond to the selected p_values
		"""

		likelihood = self.reduced_likelihood
		self.original_p_values = levels

		#Check sanity of input, likelihood must be normalized
		assert likelihood.ndim == 2
		np.testing.assert_approx_equal(likelihood.sum(),1.0)

		#Initialize list of likelihood values
		values = list()
		p_values = list()
		f = stats.chi2(2)

		#Maximum value of the likelihood
		max_likelihood = likelihood.max()

		#Initial step for the search
		step = max_likelihood
		direction = 0 

		#Loop through levels to find corresponding likelihood values
		for level in levels:

			#Iteration counter
			iterations = 0

			#Start with a guess based on a chi2 distribution with 2 degrees of freedom
			value = max_likelihood*np.exp(-0.5*f.ppf(level))
			confidence_integral = likelihood[likelihood > value].sum() 

			#Continue looping until we reach the requested precision
			while np.abs(confidence_integral/level - 1.0) > epsilon:

				#Break loop if too many iterations
				iterations += 1
				if iterations > max_iterations:
					break

				if confidence_integral>level:
					
					if direction==-1:
						logging.debug("Change direction, accuracy={0}".format(np.abs(confidence_integral/level - 1.0)))
						step /= 10.0
					value += step
					direction = 1
				
				else:

					if direction==1:
						logging.debug("Change direction, accuracy={0}".format(np.abs(confidence_integral/level - 1.0)))
						step /= 10.0
					value -= step
					direction = -1

				confidence_integral = likelihood[likelihood > value].sum() 

			#Append the found likelihood value to the output
			values.append(value)
			p_values.append(confidence_integral)

		#Return
		self.computed_p_values = p_values
		self.likelihood_values = values
		
		return values

	######################################################################
	##############Plot the contours on top of the likelihood##############
	######################################################################

	def plotContours(self,colors=["red","green","blue"],display_percentages=True,display_maximum=True,fill=False,**kwargs):

		"""
		Display the confidence likelihood contours

		"""

		if not hasattr(self,"likelihood_values"):
			self.getLikelihoodValues(levels=[0.683,0.95,0.997])

		assert len(colors) >= len(self.likelihood_values)

		extent = self.extent
		likelihood = self.reduced_likelihood.transpose()
		values = self.likelihood_values

		unit_j = (extent[1] - extent[0])/(likelihood.shape[1] - 1)
		unit_i = (extent[3] - extent[2])/(likelihood.shape[0] - 1) 

		#Build contour levels
		fmt = dict()
		
		for n,value in enumerate(values):
			fmt[value] = "{0:.1f}%".format(self.computed_p_values[n]*100)

		if fill:
			self.contour = self.ax.contourf(likelihood,values,colors=colors,origin="lower",extent=extent,aspect="auto",**kwargs)
		else:
			self.contour = self.ax.contour(likelihood,values,colors=colors,origin="lower",extent=extent,aspect="auto",**kwargs)

		#Contour labels
		self.ax.proxy += [ plt.Rectangle((0,0),1,1,fc=color) for color in colors if color!=rc.func_globals["rcParams"]["axes.facecolor"] ]
		
		if display_percentages:
			plt.clabel(self.contour,fmt=fmt,inline=1,fontsize=9)

		if display_maximum:
			
			#Find the maximum
			likelihood_max = likelihood.max()
			imax,jmax = np.where(likelihood==likelihood_max)

			#Plot scaling to physical values
			self.ax.plot(extent[0] + np.arange(likelihood.shape[1])*unit_j,np.ones(likelihood.shape[1])*imax[0]*unit_i + extent[2],linestyle="--",color="green")
			self.ax.plot(extent[0] + np.ones(likelihood.shape[0])*jmax[0]*unit_j,extent[2] + np.arange(likelihood.shape[0])*unit_i,linestyle="--",color="green")