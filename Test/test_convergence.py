try:
	
	from lenstools.topology import ConvergenceMap

except ImportError:
	
	import sys
	sys.path.append("..")
	from lenstools.topology import ConvergenceMap

import numpy as np
import matplotlib.pyplot as plt


test_map = ConvergenceMap("map.fit")

#Set bin edges
l_edges = np.arange(200.0,50000.0,200.0)
thresholds_mf = np.arange(-2.0,2.0,0.2)
thresholds_pk = np.arange(-1.0,5.0,0.2)

def test_visualize():

	assert test_map.kappa.dtype == np.float
	assert type(test_map.side_angle) == np.float

	fig,ax = plt.subplots()
	ax.imshow(test_map.kappa,origin="lower",interpolation="nearest",extent=[0,test_map.side_angle,0,test_map.side_angle])
	ax.set_xlabel(r"$x$(deg)")
	ax.set_ylabel(r"$y$(deg)")
	plt.savefig("map.png")
	plt.clf()

def test_power():

	#Compute
	l,Pl = test_map.powerSpectrum(l_edges)
	assert type(l)==np.ndarray
	assert type(Pl)==np.ndarray

	#Visualize
	fig,ax = plt.subplots()
	ax.plot(l,l*(l+1)*Pl/(2.0*np.pi))
	ax.set_xscale("log")
	ax.set_yscale("log")
	ax.set_xlabel(r"$l$")
	ax.set_ylabel(r"$l(l+1)P_l/2\pi$")

	plt.savefig("power_spectrum.png")
	plt.clf()

def test_minkowski():

	#Compute
	nu,V0,V1,V2 = test_map.minkowskiFunctionals(thresholds_mf,norm=True)

	#Assert computation went OK
	assert hasattr(test_map,"gradient_x")
	assert hasattr(test_map,"gradient_y")
	assert hasattr(test_map,"hessian_xx")
	assert hasattr(test_map,"hessian_yy")
	assert hasattr(test_map,"hessian_xy")

	#Visualize
	fig,ax = plt.subplots(1,3,figsize=(24,8))
	ax[0].plot(nu,V0)
	ax[1].plot(nu,V1)
	ax[2].plot(nu,V2)

	ax[0].set_xlabel(r"$\nu=\kappa/\sigma$")
	ax[0].set_ylabel(r"$V_0(\nu)$")

	ax[1].set_xlabel(r"$\nu=\kappa/\sigma$")
	ax[1].set_ylabel(r"$V_1(\nu)$")

	ax[2].set_xlabel(r"$\nu=\kappa/\sigma$")
	ax[2].set_ylabel(r"$V_2(\nu)$")

	fig.tight_layout()

	plt.savefig("minkowski.png")
	plt.clf()

def test_peaks():

	#Compute
	nu,pk = test_map.peakCount(thresholds_pk,norm=True)

	#Check if computation went OK
	assert type(nu)==np.ndarray
	assert type(pk)==np.ndarray

	#Visualize
	fig,ax = plt.subplots()
	ax.plot(nu,pk)
	ax.set_xlabel(r"$\nu=\kappa/\sigma$")
	ax.set_ylabel(r"$dN/d\nu$")

	plt.savefig("peaks.png")