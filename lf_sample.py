import pyfits as pf
from utils.fits_util import *
from astropy.table import Table, Column
#from LF_util import *
import LF_util
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

import cosmolopy as cosmo
default_cosmo = {'omega_M_0':0.3, 'omega_lambda_0':0.7, 'omega_k_0':0.0, 'h':0.70}


#from cosmos_sample_util import *
#from sdss_sample_util import *
#from lf_by_mass_util import *


#If no file is provided a cosmology of (Omega_Matter, Omega_Lambda, Omega_k, H0) = (0.3, 0.7, 0.0, 70.0) is assumed.
#default_cosmo = {'omega_M_0':0.3, 'omega_lambda_0':0.7, 'omega_k_0':0.0, 'h':0.70}
#default_cosmo = {'omega_M_0':0.3, 'omega_lambda_0':0.7, 'h':0.70}
#cosmo.distance.set_omega_k_0(default_cosmo)

#print "NB: have you run sdss_BH_rlf.py?"

#name2 = 'COSMOS'


### selections on full sample ###

#define samples
#sampleA = {'name': "1", 'zlim_low': , 'zlim_high':  }







#class lf:
    #pass
    
    

#class lf_subsample(lf_sample):
    #pass

class lf_sample:
  
  
    def __init__(self, name, cat, zlow=0, zhigh=20, radio_fluxlim_faint=np.nan, opt_fluxlim_faint=np.nan, opt_fluxlim_bright=np.nan, area=np.nan, rmsmap=None, completeness=None):
        
        
        self.name = name
        self.zlim_low = zlow
        self.zlim_high = zhigh
        
        
        Vzlow = cosmo.distance.comoving_volume(self.zlim_low, **default_cosmo)
        Vzhigh = cosmo.distance.comoving_volume(self.zlim_high, **default_cosmo)
        self.Vzlim_low = Vzlow
        self.Vzlim_high = Vzhigh
        
        self.cat = cat
        self.Nsrcs = len(cat)
        
        self.area = area
        
        self.rmsmap = None
        if rmsmap is not None:
            if isinstance(rmsmap, LF_util.rmsmapz):
                self.rmsmap = rmsmap
            elif isinstance(rmsmap, str):
                if os.path.exists(rmsmap):
                    self.rmsmap = LF_util.rmsmapz(rmsmap)
                    self.rmsmap.interp_setup(1e21,1e28,5.0)
                    # update area
                    A = self.rmsmap.area *(np.pi/180.)**2  # in sterad
                    if A != self.area:
                        print 'WARNING updating area, using {A:.3f} deg^2 from the rms map'.format(A=A/(np.pi/180.)**2) 
                        self.area = A
                    
                else:
                    print "WARNING given rmsmap {map:s} does not exist, continuing without".format(map=rmsmap)
            else:
                print "WARNING given rmsmap type not understood, continuing without"
            
        self.completeness = None
        if completeness is not None:
            if isinstance(completeness, LF_util.completenessf):
                self.completeness = completeness
            elif isinstance(completeness, str):
                if os.path.exists(completeness):
                    self.completeness = LF_util.completenessf(completeness)
                else:
                    print "WARNING given completeness {map:s} does not exist, continuing without".format(map=completeness)
            else:
                    print "WARNING given completeness type not understoof, continuing without".format(map=completeness)
        
        
        self.radio_fluxlim_faint = radio_fluxlim_faint
        self.opt_fluxlim_faint = opt_fluxlim_faint
        self.opt_fluxlim_bright = opt_fluxlim_bright
    
        self.set_power_z_limit()
        
        
        self.LF_x = None
        self.LF_xerr = None
        self.LF_rho = None
        self.LF_rhoerrup = None
        self.LF_rhoerrlow = None
        self.LF_num = None
        
        self.CLF_x = None
        self.CLF_xerr = None
        self.CLF_rho = None
        self.CLF_rhoerrup = None
        self.CLF_rhoerrlow = None
        self.CLF_num = None
        
        self.rhoPlim_x = None
        self.rhoPlim_xerr = None
        self.rhoPlim_rho = None
        self.rhoPlim_rhoerrup = None
        self.rhoPlim_rhoerrlow = None
        self.rhoPlim_num = None
        
        return
    
    def copy(self):
        return lf_sample(self.name, self.cat, zlow=self.zlim_low, zhigh=self.zlim_high, radio_fluxlim_faint=self.radio_fluxlim_faint, opt_fluxlim_faint=self.opt_fluxlim_faint, opt_fluxlim_bright=self.opt_fluxlim_bright, area=self.area, rmsmap=self.rmsmap, completeness=self.completeness)
    
    def copy_subcat(self, name, cat):
        return lf_sample(name, cat, zlow=self.zlim_low, zhigh=self.zlim_high, radio_fluxlim_faint = self.radio_fluxlim_faint, opt_fluxlim_faint=self.opt_fluxlim_faint, opt_fluxlim_bright=self.opt_fluxlim_bright, area=self.area, rmsmap=self.rmsmap, completeness=self.completeness)
    
    
    def sub_z_sample(self, name, zlow, zhigh,forcecalc=False, savefiles=True, plot=False):
        ''' make a new subsample with name 'name' from the z range provided'''
        
        #new_self = self.copy()
        #new_self.name = name
        thisname = self.name
        
        
        ind_z = np.where((self.cat['z'] > zlow) & (self.cat['z'] <= zhigh))[0]
        # handle no sources in selection
        if len(ind_z) == 0:
            return None
        print 'subsample z : {n1} out of {n2} sources selected '.format(n1=len(ind_z),n2=len(self.cat))
        new_self = self.sub_sample_ind(thisname+name, ind_z)
        
        new_self.zlim_low = zlow
        new_self.zlim_high = zhigh
        new_self.Vzlim_low = cosmo.distance.comoving_volume(zlow, **default_cosmo)
        new_self.Vzlim_high = cosmo.distance.comoving_volume(zhigh, **default_cosmo)
        
        new_self.set_power_z_limit()
        
        #new_self.calc_zmin_zmax()
        new_self.calc_Vzmin_Vzmax(forcecalc=forcecalc, savefiles=savefiles, plot=plot)
        
        return new_self
    
    
    def sub_sample_by_field(self, name, field, fieldlimlow, fieldlimhigh, req_new_volumes=False, plot=False):
        ''' make a new subsample with name 'name' from the z range provided'''
        
        #new_self = self.copy()
        #new_self.name = name
                
        ind = np.where((self.cat[field] > fieldlimlow) & (self.cat[field] <= fieldlimhigh))[0]
        # handle no sources in selection
        if len(ind) == 0:
            return None
        print 'subsample {n} : {n1} out of {n2} sources selected on field {f}'.format(n=name,n1=len(ind),n2=len(self.cat),f=field)
        new_self = self.sub_sample_ind(name, ind)
        
        # calculate new zmin, zmax if needed
        if req_new_volumes:
            #new_self.calc_zmin_zmax()
            new_self.calc_Vzmin_Vzmax(plot=plot)
        
        return new_self
    
    def sub_sample_ind(self, name, ind):
        ''' make a new subsample with name 'name' from the catalogue indicies'''
        
        # handle no sources in selection
        if len(ind) == 0:
            return None
        new_self = self.copy_subcat(name, self.cat[ind])
        #new_self.name = name
        #new_self.cat = new_self.cat[ind]
        #new_self.Nsrcs = len(new_self.cat)
        
        return new_self
    
    #def load_cat(self, cat, fluxunit='mJy'):
        
        ## subsample #

        #cat = cat.copy()



        #self.zz = cat.z
        
        #fKmag = cat.Ks_tot   # in fluxes in cat
        ##fKmag2 = 3631.*10.**(-0.4*Kmag2)    # AB mag
        #self.Klum = OpticalLuminosity(fKmag, zz)
        
        #scaleflux = 1.
        #if fluxunit == 'mJy':
            #scaleflux = 1e-3
        #elif fluxunit == 'Jy':
            #scaleflux = 1.
            
        #self.ff = (cat.Si_1_4_)*scaleflux   #in Jy
        #self.power = np.log10(RadioPower(self.ff, self.zz, alpha=0.8))  # assumed spec ind

        #self.Fcor = np.ones(len(ff))
        #self.areal = get_area_for_flux(ff)

        ## stellar masses
        #self.smass = cat_vlacosmos.lmass


        #self.Nsrc = len(zz)
        
        #vals = func()
        
        #self.z = vals['z']
        #self.optical_flux = vals['optical_flux']
        #self.optical_flux = vals['optical_flux']
        #self.Nsrc =  
        
        #return
    
    def plot_zmin_zmax(self):
        
        f=plt.figure()
        if 'zmax' in self.cat.dtype.names:
            plt.scatter(self.cat['power'], self.cat['zmax'], c=self.cat['z'], marker='v', s=20, edgecolor='none')
        if 'Pzmax' in self.cat.dtype.names:
            plt.scatter(self.cat['power'], self.cat['Pzmax'], c=self.cat['z'], marker='v', s=10, edgecolor='none')
        if 'Optzmax' in self.cat.dtype.names:
            plt.scatter(self.cat['power'], self.cat['Optzmax'], c=self.cat['z'], marker='v', s=10, edgecolor='none')
        if 'Optzmin' in self.cat.dtype.names:
            plt.scatter(self.cat['power'], self.cat['Optzmin'], c=self.cat['z'], marker='^', s=10, edgecolor='none')
        if 'zmin' in self.cat.dtype.names:
            plt.scatter(self.cat['power'], self.cat['zmin'], c=self.cat['z'], marker='^', s=20, edgecolor='none')
        plt.minorticks_on()
        plt.xlabel("power")
        plt.ylabel("z min/max")
        plt.savefig('sample_zmax_zmin_{name}.png'.format(name=self.name))
        plt.close(f)
        
        return
    
    def plot_Vzmin_Vzmax(self, logV=True):
        
        f=plt.figure()
        if 'Vzmax' in self.cat.dtype.names:
            c = plt.scatter(self.cat['power'], self.cat['Vzmax'], c=self.cat['z'], marker='v', s=20, vmin=0, vmax=3, edgecolor='none',label='Max')
        if 'PVzmax' in self.cat.dtype.names:
            c = plt.scatter(self.cat['power'], self.cat['PVzmax'], c=self.cat['z'], marker='v', s=10, vmin=0, vmax=3, edgecolor='none',label='Pmax')
        if 'PVzmin' in self.cat.dtype.names:
            c = plt.scatter(self.cat['power'], self.cat['PVzmin'], c=self.cat['z'], marker='^', s=10, vmin=0, vmax=3, edgecolor='none',label='Pmin')
        if 'OptVzmax' in self.cat.dtype.names:
            c = plt.scatter(self.cat['power'], self.cat['OptVzmax'], c=self.cat['z'], marker='1', s=10, vmin=0, vmax=3, edgecolor='none',label='Optmax')
        if 'OptVzmin' in self.cat.dtype.names:
            c = plt.scatter(self.cat['power'], self.cat['OptVzmin'], c=self.cat['z'], marker='^', s=10, vmin=0, vmax=3, edgecolor='none',label='Optmin')
        if 'Vzmin' in self.cat.dtype.names:
            c = plt.scatter(self.cat['power'], self.cat['Vzmin'], c=self.cat['z'], marker='2', s=20, vmin=0, vmax=3, edgecolor='none',label='Min')
        if logV:
            plt.semilogy()
        plt.colorbar(c)
        plt.legend(loc='upper left')
        plt.minorticks_on()
        plt.xlabel("power")
        x1,x2 = plt.xlim()
        plt.hlines(self.Vzlim_low, x1, x2, 'gray', alpha=0.5)
        plt.hlines(self.Vzlim_high, x1, x2, 'gray', alpha=0.5)
        plt.text(x1, self.Vzlim_low, str(self.zlim_low))
        plt.text(x1, self.Vzlim_high, str(self.zlim_high))
        plt.xlim(x1,x2)
        plt.ylabel("Vz min/max")
        plt.savefig('sample_Vzmax_Vzmin_{name}.png'.format(name=self.name))
        plt.close(f)
        
        return
    
    def calc_zmin_zmax(self, plot=False):
        
        haspower = False
        if 'power' in self.cat.dtype.names:
            haspower = True
        
        if haspower:
            print "getting zmin zmax for radio-optical sample {n}".format(n=self.name)
        else:
            print "getting zmin zmax for optical sample {n}".format(n=self.name)
        
        #at what redshift does each source fall below the flux density limit?
        if haspower:
            Pzmax = LF_util.get_zmax(self.cat['z'], 10.**self.cat['power'], self.radio_fluxlim_faint, stype='Radio',filename='zmax.radio.sav.%s.npy' %(self.name), clobber=0)
        Optzmax = LF_util.get_zmax(self.cat['z'], self.cat['opt_lum'], self.opt_fluxlim_faint, stype='Optical',filename='zmax.optical.sav.%s.npy' %(self.name), clobber=0)
        Optzmin = LF_util.get_zmin(self.cat['z'], self.cat['opt_lum'], self.opt_fluxlim_bright, stype='Optical',filename='zmin.optical.sav.%s.npy' %(self.name), clobber=0)

        if haspower:
            if 'Pzmax' not in self.cat.dtype.names:
                self.cat.add_column(Column(Pzmax, 'Pzmax') )
            else:
                self.cat['Pzmax'] = Pzmax
            
        if 'Optzmax' not in self.cat.dtype.names:
            self.cat.add_column(Column(Optzmax, 'Optzmax') )
            self.cat.add_column(Column(Optzmin, 'Optzmin') )
        else:
            self.cat['Optzmax'] = Optzmax
            self.cat['Optzmin'] = Optzmin

        #np.savez('sample_{name}.npz'.format(name=self.name), z=self.cat['z'], sm=self.smass, P=self.power )
        
        if plot:
            self.plot_zmin_zmax()
        
        if haspower:
            ### Combine zmax's from radio, optical and z selections
            zmax = self.zlim_high*np.ones(len(Optzmax))
            t1 = np.minimum(Optzmax, Pzmax)
            t2 = np.minimum(t1, zmax)
            zmax = t2
        else:
            ### Combine zmax's from radio, optical and z selections
            zmax = self.zlim_high*np.ones(len(Optzmax))
            t2 = np.minimum(Optzmax, zmax)
            zmax = t2
                
                
        ### Combine zmins's from optical and z selections
        zmin = self.zlim_low*np.ones(len(Optzmin))
        t1 = np.maximum(Optzmin, zmin)
        zmin = t1
        
        if 'zmin' not in self.cat.dtype.names:
            self.cat.add_column(Column(zmin, 'zmin'))
        else:
            self.cat['zmin'] = zmin
            
        if 'zmax' not in self.cat.dtype.names:
            self.cat.add_column(Column(zmax, 'zmax'))
        else:
            self.cat['zmax'] = zmax
            
            
        if 'Fcor' not in self.cat.dtype.names:
            self.cat.add_column(Column(np.ones(len(zmax)), 'Fcor'))
        else:
            self.cat['Fcor'] = np.ones(len(zmax))
            
        if 'areal' not in self.cat.dtype.names:
            self.cat.add_column(Column(np.ones(len(zmax)), 'areal'))
        else:
            self.cat['areal'] = np.ones(len(zmax))

        
        return
    
    
    def calc_Vzmin_Vzmax(self, plot=True, verbose=True, forcecalc=False, savefiles=True):
        
        haspower = False
        if 'power' in self.cat.dtype.names:
            haspower = True
        
        if haspower:
            print "getting Vzmin Vzmax for radio-optical sample {n}".format(n=self.name)
        else:
            print "getting Vzmin Vzmax for optical sample {n}".format(n=self.name)
        
        #at what redshift does each source fall below the flux density limit?
        if haspower:
            PVzmax = LF_util.get_Vzmax(self.cat['z'], 10.**self.cat['power'], self.radio_fluxlim_faint, rmsmap=self.rmsmap, completeness=self.completeness, stype='Radio',filename='Vzmax.radio.sav.%s.npy' %(self.name), clobber=forcecalc, savefile=savefiles)
            PVzmin = LF_util.get_Vzmin(self.cat['z'], 10.**self.cat['power'], self.radio_fluxlim_faint, zmin=self.zlim_low, rmsmap=self.rmsmap, completeness=self.completeness, stype='Radio',filename='Vzmin.radio.sav.%s.npy' %(self.name), clobber=forcecalc, savefile=savefiles)
        OptVzmax = LF_util.get_Vzmax(self.cat['z'], self.cat['opt_lum'], self.opt_fluxlim_faint, stype='Optical',filename='Vzmax.optical.sav.%s.npy' %(self.name), clobber=forcecalc, savefile=savefiles)
        OptVzmin = LF_util.get_Vzmin(self.cat['z'], self.cat['opt_lum'], self.opt_fluxlim_bright, stype='Optical',filename='Vzmin.optical.sav.%s.npy' %(self.name), clobber=forcecalc, savefile=savefiles)
        #import ipdb
        #if haspower:
            #if np.any(PVzmin >= PVzmax):
                #ipdb.set_trace()

        if haspower:
            if 'PVzmax' not in self.cat.dtype.names:
                self.cat.add_column(Column(PVzmax, 'PVzmax'))
            else:
                self.cat['PVzmax'] = PVzmax
            if 'PVzmin' not in self.cat.dtype.names:
                self.cat.add_column(Column(PVzmin, 'PVzmin'))
            else:
                self.cat['PVzmin'] = PVzmin
            
        if 'OptVzmax' not in self.cat.dtype.names:
            self.cat.add_column(Column(OptVzmax, 'OptVzmax'))
            self.cat.add_column(Column(OptVzmin, 'OptVzmin'))
        else:
            self.cat['OptVzmax'] = OptVzmax
            self.cat['OptVzmin'] = OptVzmin

        #np.savez('sample_{name}.npz'.format(name=self.name), z=self.cat['z'], sm=self.smass, P=self.power )
        
        
        Vzlim_high = cosmo.distance.comoving_volume(self.zlim_high, **default_cosmo)
        if haspower:
            ### Combine Vzmax's from radio, optical and z selections
            Vzmax = Vzlim_high*np.ones(len(OptVzmax))
            t1 = np.minimum(OptVzmax, PVzmax)
            t2 = np.minimum(t1, Vzmax)
            Vzmax = t2
        else:
            ### Combine Vzmax's from radio, optical and z selections
            Vzmax = Vzlim_high*np.ones(len(OptVzmax))
            t2 = np.minimum(OptVzmax, Vzmax)
            Vzmax = t2
                
                
        ### Combine Vzmins's from optical and z selections
        Vzlim_low = cosmo.distance.comoving_volume(self.zlim_low, **default_cosmo)
        Vzmin = Vzlim_low*np.ones(len(OptVzmin))
        if haspower:
            ### Combine Vzmin's from radio, optical and z selections
            Vzmin = Vzlim_low*np.ones(len(OptVzmax))
            t1 = np.minimum(Vzmin, PVzmin)
            t2 = np.maximum(t1, OptVzmin)
            Vzmin = t2
            
        else:
            t1 = np.maximum(OptVzmin, Vzmin)
            Vzmin = t1
        
        if 'Vzmin' not in self.cat.dtype.names:
            self.cat.add_column(Column(Vzmin, 'Vzmin'))
        else:
            self.cat['Vzmin'] = Vzmin
            
        if 'Vzmax' not in self.cat.dtype.names:
            self.cat.add_column(Column(Vzmax, 'Vzmax'))
        else:
            self.cat['Vzmax'] = Vzmax
            
            
        if 'Fcor' not in self.cat.dtype.names:
            self.cat.add_column(Column(np.ones(len(Vzmax)), 'Fcor'))
        else:
            self.cat['Fcor'] = np.ones(len(Vzmax))
            
        if 'areal' not in self.cat.dtype.names:
            self.cat.add_column(Column(np.ones(len(Vzmax)), 'areal'))
        else:
            self.cat['areal'] = np.ones(len(Vzmax))

        
        if plot and haspower:
            self.plot_Vzmin_Vzmax()
        
        return
    
    
    def set_power_z_limit(self):
        zz = np.linspace(self.zlim_low, self.zlim_high, 10)
        Plim = np.log10(LF_util.RadioPower(self.radio_fluxlim_faint, zz, alpha=0.8)) 
        self.power_z_limit = np.vstack((zz, Plim))
        return
    
    
    
    def compute_LF(self, pgrid, maskbins=None, CV_f=None, ignoreMinPower=False):
        
        
        logp_radio_lf = (pgrid[:-1]+pgrid[1:])/2.
        dlogp_radio_lf = (pgrid[1:]-pgrid[:-1])/2.
        
        #print self.cat['power']
        rho, rhoerr, num = LF_util.get_LF_rms_f_areal(pgrid, self.cat['power'], self.cat['Vzmin'], self.cat['Vzmax'], self.cat['Fcor'], self.cat['areal'], self.area, ignoreMinPower=ignoreMinPower)
        #print self.cat['power']
        #print pgrid
        #print type(pgrid)
        
        rhoerrlow = rhoerr
        rhoerrup = rhoerr
        
        if maskbins is not None:
            if isinstance(maskbins, np.ndarray):
                if len(maskbins) == 2:
                    if np.isfinite(maskbins[0]): 
                        rho[logp_radio_lf<=maskbins[0]] *= np.nan
                        rhoerrlow[logp_radio_lf<=maskbins[0]] *= np.nan
                        rhoerrup[logp_radio_lf<=maskbins[0]] *= np.nan
                    if np.isfinite(maskbins[1]): 
                        rho[logp_radio_lf>=maskbins[1]] *= np.nan
                        rhoerrlow[logp_radio_lf>=maskbins[1]] *= np.nan
                        rhoerrup[logp_radio_lf>=maskbins[1]] *= np.nan
                else:
                    print "maskbins invalid"
            else:
                print "maskbins invalid"
            
        #print '###', rhoerrup
        # add cosmic variance errors #
        if CV_f is not None:
            #self.LF_rhoerrup = np.sqrt(self.LF_rhoerrup**2. + (num*CV_f)**2.)
            #self.LF_rhoerrlow = np.sqrt(self.LF_rhoerrlow**2. + (num*CV_f)**2.)
            #rhoerrup = np.sqrt(rhoerrup**2. + (CV_f*rho)**2.)
            #rhoerrlow = np.sqrt(rhoerrlow**2. + (CV_f*rho)**2.)
            rhoerrup = rhoerrup*np.sqrt(1 + (CV_f)**2.)
            rhoerrlow = rhoerrlow*np.sqrt(1 + (CV_f)**2.)
            
        #print '###', rhoerrup
            
        # fix lower errors to be rho - for plotting logscale #
        rhoerrlow[rhoerrlow>=rho] = rho[rhoerrlow>=rho]*0.9999
        
        self.LF_x = logp_radio_lf
        self.LF_xerr = dlogp_radio_lf
        self.LF_rho = rho
        self.LF_rhoerrup = rhoerrup
        self.LF_rhoerrlow = rhoerrlow
        self.LF_num = num
        
        
        #print '* xact',logp_radio_lf
        #print '* x',self.LF_x
        #print '* xerract',dlogp_radio_lf
        #print '* xerr',self.LF_xerr
        #print '* rhoact',rho
        #print '* rho',self.LF_rho
        
        return rho, rhoerrlow, rhoerrup, num

    def compute_SMF(self, smgrid, masscompleteness):
        '''
masscompleteness - mass(z) function describing the completeness envelope
        '''
        
        logsm = (smgrid[:-1]+smgrid[1:])/2.
        dlogsm = (smgrid[1:]-smgrid[:-1])/2.
        
        
        # select mass-complete #
        smenv_ind =  np.where(self.cat['smass'] >= masscompleteness(z=self.cat['z']))[0]  # Stellar mass cut #
        print "{n1} of {n2} sources selected on SM envelope".format(n2=len(self.cat),n1= len(smenv_ind))
        sm_complete_sample = self.sub_sample_ind('m', smenv_ind )
        
        # zmax determined from mass-completeness also #
        SMzmax = masscompleteness(m=sm_complete_sample.cat['smass'])
        VSMzmax = cosmo.distance.comoving_volume(SMzmax, **default_cosmo)
        #sm_complete_sample.cat['Vzmax']=
        newVSMzmax = np.minimum(sm_complete_sample.cat['Vzmax'], VSMzmax)
        
        #import ipdb
        #ipdb.set_trace()
    
        
        #print self.cat['power']
        #rho, rhoerr, num = LF_util.get_LF_rms_f_areal(smgrid, sm_complete_sample.cat['smass'], sm_complete_sample.cat['Vzmin'], sm_complete_sample.cat['Vzmax'], sm_complete_sample.cat['Fcor'], sm_complete_sample.cat['areal'], sm_complete_sample.area, xstr="SM")
        rho, rhoerr, num = LF_util.get_LF_rms_f_areal(smgrid, sm_complete_sample.cat['smass'], sm_complete_sample.cat['Vzmin'], newVSMzmax, sm_complete_sample.cat['Fcor'], sm_complete_sample.cat['areal'], sm_complete_sample.area, xstr="SM")
        
        
        #print self.cat['power']
        #print pgrid
        #print type(pgrid)
        
        # fix lower errors to be rho #
        rhoerrlow = rhoerr
        rhoerrup = rhoerr
        rhoerrlow[rhoerrlow>=rho] = rho[rhoerrlow>=rho]*0.9999
        
        self.SMF_x = logsm
        self.SMF_xerr = dlogsm
        self.SMF_rho = rho
        self.SMF_rhoerrup = rhoerrup
        self.SMF_rhoerrlow = rhoerrlow
        self.SMF_num = num
        
        #print '* xact',logp_radio_lf
        #print '* x',self.LF_x
        #print '* xerract',dlogp_radio_lf
        #print '* xerr',self.LF_xerr
        #print '* rhoact',rho
        #print '* rho',self.LF_rho
        
        return rho, rhoerrlow, rhoerrup, num
    
    
    def compute_CLF(self,  pgrid):
        
        logp_radio_lf = (pgrid[:-1]+pgrid[1:])/2.
        dlogp_radio_lf = (pgrid[1:]-pgrid[:-1])/2.
        
        rho, rhoerr, num = LF_util.get_CLF_f_areal(pgrid, self.cat['power'], self.cat['zmin'], self.cat['zmax'], self.cat['Fcor'], self.cat['areal'], self.area)
        
        # fix lower errors to be rho #
        rhoerrlow = rhoerr
        rhoerrup = rhoerr
        rhoerrlow[rhoerrlow>=rho] = rho[rhoerrlow>=rho]*0.9999
        
        self.CLF_x = logp_radio_lf
        self.CLF_xerr = dlogp_radio_lf
        self.CLF_rho = rho
        self.CLF_rhoerrup = rhoerrup
        self.CLF_rhoerrlow = rhoerrlow
        self.CLF_num = num
        
        return rho, rhoerrlow, rhoerrup, num
    
    
    def compute_rhoPlim(self,  Plimit):
        
        
        rho, rhoerr, num = LF_util.get_rho_Plim_f_areal(Plimit, self.cat['power'], self.cat['zmin'], self.cat['zmax'], self.cat['Fcor'], self.cat['areal'], self.area, xstr="SM")
        
        # fix lower errors to be rho #
        rhoerrlow = rhoerr
        rhoerrup = rhoerr
        if rhoerrlow>=rho:
            rhoerrlow = rho*0.9999
        
        self.rhoPlim_plim = Plimit
        self.rhoPlim_rho = rho
        self.rhoPlim_rhoerrup = rhoerrup
        self.rhoPlim_rhoerrlow = rhoerrlow
        self.rhoPlim_num = num
        
        return rho, rhoerrlow, rhoerrup, num
    
    
        
    
    
    
    
    
    
    
    
    
    
    
  