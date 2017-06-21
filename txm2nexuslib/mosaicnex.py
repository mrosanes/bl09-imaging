#!/usr/bin/python

"""
(C) Copyright 2014 Marc Rosanes
The program is distributed under the terms of the 
GNU General Public License.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from OleFileIO_PL import *   
import numpy as np
import nxs
import sys
import struct
import datetime
import time
import argparse


class mosaicnex:

    def __init__(self, files, files_order='s', title='X-ray Mosaic', 
                 sourcename='ALBA', sourcetype='Synchrotron X-ray Source', 
                 sourceprobe='x-ray', instrument='BL09 @ ALBA', 
                 sample='Unknown'): 

        self.files=files 
        self.num_input_files = len(files) #number of files.
        self.orderlist = list(files_order)
        #number of 's' (sample), 'b' (brightfield (FF)) and 'd' (darkfield).    
        self.num_input_files_verify = len(self.orderlist) 

        self.exitprogram = 0
        if(self.num_input_files != self.num_input_files_verify):
            print('Number of input files must be equal ' + 
                  'to number of characters of files_order.\n')
            self.exitprogram=1
            return
                   
        if 's' not in files_order:
            print('Mosaic data file (xrm) has to be specified, ' + 
                  'inicate it as \'s\' in the argument option -o.\n')
            self.exitprogram=1
            return

        index_sample_file = files_order.index('s')
        self.mosaic_file_xrm = self.files[index_sample_file]        
        self.filename_hdf5 = self.mosaic_file_xrm.split('.xrm')[0] + '.hdf5'

        self.index_FF_file= -1
        self.brightexists = 0
        for i in range (0, self.num_input_files):
            #Create bright field structure    
            if(self.orderlist[i] == 'b'):
                self.mosaic_file_FF_xrm = self.files[i]  
                self.index_FF_file= i
                self.brightexists = 1
                self.numrowsFF = 0
                self.numcolsFF = 0
                self.nSampleFramesFF = 1
                self.datatypeFF = 'uint16'
                                    
        self.title = title
        self.sourcename = sourcename
        self.sourcetype = sourcetype
        self.sourceprobe = sourceprobe
        self.instrumentname = instrument
        self.samplename = sample
        self.sampledistance = 0
        self.datatype = 'uint16' #two bytes
        self.sequence_number = 0
        self.sequence_number_sample=0
        
        self.programname = 'mosaic2nexus.py'
        self.nxentry = 0
        self.nxsample = 0
        self.nxmonitor = 0
        self.nxinstrument = 0
        self.nxdata = 0
        #self.nxdataFF = 0
        
        self.nxdetectorsample = 0
        
        self.numrows = 0
        self.numcols = 0
        self.nSampleFrames = 0

        self.monitorsize = self.nSampleFrames 
        self.monitorcounts = 0
        return
     
    def NXmosaic_structure(self):    
        #create_basic_structure
    
        self.nxentry = nxs.NXentry(name= "NXmosaic") 
        
        self.nxentry['title']=self.mosaic_file_xrm
        self.nxentry['definition'] = 'NXtomo'
        
        self.nxsample = nxs.NXsample()
        self.nxentry.insert(self.nxsample)
        self.nxsample['name'] = self.samplename

        self.nxmonitor = nxs.NXmonitor(name= 'control')
        self.nxentry.insert(self.nxmonitor)

        self.nxdata = nxs.NXdata()
        self.nxentry.insert(self.nxdata)

        #self.nxdataFF = nxs.NXdata()
        #self.nxentry.insert(self.nxdataFF)
        
        self.nxinstrument = nxs.NXinstrument(name= 'instrument')
        self.nxinstrument['name'] = self.instrumentname        
        self.nxentry.insert(self.nxinstrument)

        self.nxsource = nxs.NXsource(name = 'source')
        self.nxinstrument.insert(self.nxsource)
        self.nxinstrument['source']['name'] = self.sourcename
        self.nxinstrument['source']['type'] = self.sourcetype
        self.nxinstrument['source']['probe'] = self.sourceprobe

        self.nxdetectorsample = nxs.NXdetector(name = 'sample')
        self.nxinstrument.insert(self.nxdetectorsample)  

        self.nxentry.save(self.filename_hdf5, 'w5')

        return 

    #### Function used to convert the metadata from .xrm to NeXus .hdf5
    def convert_metadata(self):

        verbose = False
        print("Trying to convert xrm metadata to NeXus HDF5.")
        
        #Opening the .xrm files as Ole structures
        ole = OleFileIO(self.mosaic_file_xrm)
        #xrm files have been opened


        self.nxentry['program_name'] = self.programname
        self.nxentry['program_name'].attrs['version']='1.0'
        self.nxentry['program_name'].attrs['configuration'] = (self.programname 
                                                      + ' ' 
                                                      + ' '.join(sys.argv[1:]))
        self.nxentry['program_name'].write()
                                                              
        # SampleID
        if ole.exists('SampleInfo/SampleID'):   
            stream = ole.openstream('SampleInfo/SampleID')
            data = stream.read()
            struct_fmt ='<'+'50s' 
            samplename = struct.unpack(struct_fmt, data)
            if self.samplename != 'Unknown':
                self.samplename = samplename[0]    
            if verbose: 
                print "SampleInfo/SampleID: %s " % self.samplename 
            self.nxsample['name'] = nxs.NXfield(
                name = 'name', value = self.samplename)    
            self.nxsample['name'].write()    
        else:
            print("There is no information about SampleID")
	            
        # Pixel-size
        if ole.exists('ImageInfo/PixelSize'):   
            stream = ole.openstream('ImageInfo/PixelSize')
            data = stream.read()
            struct_fmt = '<1f'
            pixelsize = struct.unpack(struct_fmt, data)
            pixelsize = pixelsize[0]
            if verbose: 
                print "ImageInfo/PixelSize: %f " %  pixelsize  
            self.nxinstrument['sample']['x_pixel_size'] = nxs.NXfield(
                name='x_pixel_size', value = pixelsize, attrs = {'units': 'um'})
            self.nxinstrument['sample']['x_pixel_size'].write()    
            self.nxinstrument['sample']['y_pixel_size'] = nxs.NXfield(
                name='y_pixel_size', value = pixelsize, attrs = {'units': 'um'}) 
            self.nxinstrument['sample']['y_pixel_size'].write()    
        else:
            print("There is no information about PixelSize")

        # Accelerator current (machine current)
        if ole.exists('ImageInfo/Current'):   
            stream = ole.openstream('ImageInfo/Current')
            data = stream.read()
            struct_fmt = '<1f'
            current = struct.unpack(struct_fmt, data)
            current = current[0]
            if verbose: 
                print "ImageInfo/Current: %f " %  current  
            self.nxinstrument['sample']['current'] = nxs.NXfield(
                name = 'current', value=current, attrs = {'units': 'mA'})
            self.nxinstrument['sample']['current'].write()
        else:
            print("There is no information about Current")
    
        # Mosaic data size 
        if (ole.exists('ImageInfo/NoOfImages') and 
            ole.exists('ImageInfo/ImageWidth') and 
            ole.exists('ImageInfo/ImageHeight')):                  
                    
            stream = ole.openstream('ImageInfo/NoOfImages')
            data = stream.read()
            nimages = struct.unpack('<I', data)
            if verbose: 
                print "ImageInfo/NoOfImages = %i" % nimages[0] 
            self.nSampleFrames = np.int(nimages[0])
        
            stream = ole.openstream('ImageInfo/ImageHeight')
            data = stream.read()
            ximage = struct.unpack('<I', data)    
            if verbose: 
                print "ImageInfo/ImageHeight = %i" % ximage[0]  
            self.numrows = np.int(ximage[0])
            
            stream = ole.openstream('ImageInfo/ImageWidth')
            data = stream.read()
            yimage = struct.unpack('<I', data)
            if verbose: 
                print "ImageInfo/ImageWidth = %i" % yimage[0]  
            self.numcols = np.int(yimage[0])

        else:
            print('There is no information about the mosaic size ' +
                  '(ImageHeight, ImageWidth or Number of images)')

 	    # FF data size 
        if(self.brightexists == 1): 
            oleFF = OleFileIO(self.mosaic_file_FF_xrm)
            if (ole.exists('ImageInfo/NoOfImages') 
                and oleFF.exists('ImageInfo/ImageWidth') 
                and oleFF.exists('ImageInfo/ImageHeight')):                  
                        
                stream = oleFF.openstream('ImageInfo/NoOfImages')
                data = stream.read()
                nimages = struct.unpack('<I', data)
                if verbose: 
                    print "ImageInfo/NoOfImages = %i" % nimages[0] 
                self.nSampleFramesFF = np.int(nimages[0])
            
                stream = oleFF.openstream('ImageInfo/ImageHeight')
                data = stream.read()
                ximage = struct.unpack('<I', data)    
                if verbose: 
                    print "ImageInfo/ImageHeight = %i" % ximage[0]  
                self.numrowsFF = np.int(ximage[0])
                
                stream = oleFF.openstream('ImageInfo/ImageWidth')
                data = stream.read()
                yimage = struct.unpack('<I', data)
                if verbose: 
                    print "ImageInfo/ImageWidth = %i" % yimage[0]  
                self.numcolsFF = np.int(yimage[0])   
                        
            else:
                print('There is no information about the mosaic size ' +
                      '(ImageHeight, ImageWidth or Number of images)')
            oleFF.close()    
            
        # Energy            	
        if ole.exists('ImageInfo/Energy'):
            stream = ole.openstream('ImageInfo/Energy')
    	    data = stream.read()
     	    struct_fmt = "<{0:10}f".format(self.nSampleFrames)
            # we found some xrm images (flatfields) with different encoding 
            # of data
       	    try:
                energies = struct.unpack(struct_fmt, data)
            except struct.error:
                print >> sys.stderr, ('Unexpected data length (%i bytes). ' +  
                                      'Trying to unpack Energies with: ' + 
                                      '"f"+"36xf"*(nSampleFrames-1)'%len(data))
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                energies = struct.unpack(struct_fmt, data)
            if verbose: print "ImageInfo/Energy: \n ",  energies  
            self.nxinstrument['source']['energy'] = nxs.NXfield(
                name = 'energy', value = energies, attrs = {'units': 'eV'}) 
            self.nxinstrument['source']['energy'].write()
        else:
            print('There is no information about the energies with which '  
                   'have been taken the different mosaic images')

        # DataType: 10 float; 5 uint16 (unsigned 16-bit (2-byte) integers)
        if ole.exists('ImageInfo/DataType'):                  
            stream = ole.openstream('ImageInfo/DataType')
            data = stream.read()
            struct_fmt = '<1I'
            datatype = struct.unpack(struct_fmt, data)
            datatype = int(datatype[0])
            if datatype == 5:
                self.datatype = 'uint16'
            else:
                self.datatype = 'float'
            if verbose: 
                print "ImageInfo/DataType: %s " %  self.datatype      
        else:
            print("There is no information about DataType")

        # Start and End Times 
        if ole.exists('ImageInfo/Date'):  
            stream = ole.openstream('ImageInfo/Date')       
            data = stream.read()
            dates = struct.unpack('<'+'17s23x'*self.nSampleFrames, data) 
            
            startdate = dates[0]
            [day, hour] = startdate.split(" ")
            [month, day, year] = day.split("/")
            [hour, minute, second] = hour.split(":")    
            
            year = '20'+year
            year = int(year)   
            month = int(month)
            day = int(day)
            hour = int(hour)
            minute = int(minute)
            second = int(second)

            starttime = datetime.datetime(year, month, day, 
                                          hour, minute, second)                 
            starttimeiso = starttime.isoformat()
            times = time.mktime(starttime.timetuple())

            if verbose: 
                print "ImageInfo/Date = %s" % starttimeiso 
            self.nxentry['start_time'] = str(starttimeiso)
            self.nxentry['start_time'].write()    

            enddate = dates[self.nSampleFrames-1]    
            [endday, endhour] = enddate.split(" ")
            [endmonth, endday, endyear] = endday.split("/")
            [endhour, endminute, endsecond] = endhour.split(":")

            endyear = '20'+endyear
            endyear = int(endyear)   
            endmonth = int(endmonth)
            endday = int(endday)
            endhour = int(endhour)
            endminute = int(endminute)
            endsecond = int(endsecond)

            endtime = datetime.datetime(endyear, endmonth, endday, 
                                        endhour, endminute, endsecond)                 
            endtimeiso = endtime.isoformat()
            endtimes = time.mktime(endtime.timetuple())   
            
            if verbose: 
                print "ImageInfo/Date = %s" % endtimeiso 
            self.nxentry['end_time']= str(endtimeiso)
            self.nxentry['end_time'].write()

        else:
            print("There is no information about Date")

        # Sample rotation angles 
        if ole.exists('ImageInfo/Angles'):    
            stream = ole.openstream('ImageInfo/Angles')
            data = stream.read()
            struct_fmt = '<{0:10}f'.format(self.nSampleFrames)
            angles = struct.unpack(struct_fmt, data)
            if verbose: 
                print "ImageInfo/Angles: \n ",  angles
            self.nxsample['rotation_angle'] = nxs.NXfield(
                                                    name = 'rotation_angle', 
                                                    value=angles, 
                                                    attrs={'units': 'degrees'})
            self.nxsample['rotation_angle'].write() 
            self.nxdata['rotation_angle'] = nxs.NXlink(
                target = self.nxsample['rotation_angle'], group=self.nxdata)
            self.nxdata['rotation_angle'].write()

        else:
            print('There is no information about the angles at' 
                   'which have been taken the different mosaic images')

        # Sample translations in X, Y and Z 
        # X sample translation: nxsample['z_translation']
        if ole.exists('ImageInfo/XPosition'):

            stream = ole.openstream('ImageInfo/XPosition')
            data = stream.read()
            struct_fmt = "<{0:10}f".format(self.nSampleFrames)
            # There have been found some xrm images (flatfields) with 
            # different encoding of data
            try: 
                xpositions = struct.unpack(struct_fmt, data) 
            except struct.error:
                print >> sys.stderr, ('Unexpected data length (%i bytes). ' +  
                                      'Trying to unpack XPositions with: ' + 
                                      '"f"+"36xf"*(nSampleFrames-1)'%len(data))
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                xpositions = struct.unpack(struct_fmt, data)
            if verbose: 
                print "ImageInfo/XPosition: \n ",  xpositions  

            self.nxsample['x_translation'] = nxs.NXfield(
                name = 'x_translation', value=xpositions, attrs={'units': 'mm'})   
            self.nxsample['x_translation'].write()

        else:
            print("There is no information about xpositions")

        # Y sample translation: nxsample['z_translation']
        if ole.exists('ImageInfo/YPosition'):

            stream = ole.openstream('ImageInfo/YPosition')
            data = stream.read()
            struct_fmt = "<{0:10}f".format(self.nSampleFrames)
            # we found some xrm images (flatfields) with different encoding 
            # of data.
            try:
                ypositions = struct.unpack(struct_fmt, data) 
            except struct.error:
                print >> sys.stderr, ('Unexpected data length (%i bytes). ' +  
                                      'Trying to unpack YPositions with: ' + 
                                      '"f"+"36xf"*(nSampleFrames-1)'%len(data))
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                ypositions = struct.unpack(struct_fmt, data)
            if verbose: 
                print "ImageInfo/YPosition: \n ",  ypositions  
      
            self.nxsample['y_translation'] = nxs.NXfield(
                name = 'y_translation', value=ypositions, attrs={'units': 'mm'})   
            self.nxsample['y_translation'].write()

        else:
            print("There is no information about xpositions")

        # Z sample translation: nxsample['z_translation']
        if ole.exists('ImageInfo/ZPosition'):

            stream = ole.openstream('ImageInfo/ZPosition')
            data = stream.read()
            struct_fmt = "<{0:10}f".format(self.nSampleFrames)
            # we found some xrm images (flatfields) with different encoding 
            # of data.
            try: 
                zpositions = struct.unpack(struct_fmt, data)
            except struct.error:
                print >> sys.stderr, ('Unexpected data length (%i bytes). ' +  
                                      'Trying to unpack ZPositions with: ' + 
                                      '"f"+"36xf"*(nSampleFrames-1)'%len(data))
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                zpositions = struct.unpack(struct_fmt, data)
            if verbose: 
                print "ImageInfo/ZPosition: \n ",  zpositions  
      
            self.nxsample['z_translation'] = nxs.NXfield(
                name = 'z_translation', value=zpositions, attrs={'units': 'mm'})   
            self.nxsample['z_translation'].write()

        else:
            print("There is no information about xpositions")

        # NXMonitor data: Not used in TXM microscope. 
        # Used to normalize in function fo the beam intensity (to verify). 
        # In the ALBA-BL09 case all the values will be set to 1.
        self.monitorsize = self.nSampleFrames
        self.monitorcounts = np.ones((self.monitorsize), dtype= np.uint16)
        self.nxmonitor['data'] = nxs.NXfield(
            name='data', value=self.monitorcounts)
        self.nxmonitor['data'].write()        

        ole.close()
        print ("Meta-Data conversion from 'xrm' to NeXus HDF5 has been done.\n")  
        return


    #### Converts a Mosaic image fromt xrm to NeXus hdf5.    
    def convert_mosaic(self): 

        #Bright-Field
        if not self.brightexists:
            print('\nWarning: Bright-Field is not present, normalization ' + 
                  'will not be possible if you do not insert a ' + 
                  'Bright-Field (FF). \n') 
                  
        verbose = False
        print("Converting mosaic image data from xrm to NeXus HDF5.")

        #Opening the mosaic .xrm file as an Ole structure.
        olemosaic = OleFileIO(self.mosaic_file_xrm)

        # Mosaic data image
        self.nxinstrument['sample']['data'] = nxs.NXfield(name='data', 
                                        dtype=self.datatype , 
                                        shape=[self.numrows, self.numcols])
        sample_data = self.nxinstrument['sample']['data']
        sample_data.attrs['Data Type']=self.datatype 
        sample_data.attrs['Number of Subimages'] = self.nSampleFrames
        sample_data.attrs['Image Height'] = self.numrows
        sample_data.attrs['Image Width'] = self.numcols
        sample_data.write()

        img_string = "ImageData1/Image1"
        stream = olemosaic.openstream(img_string)

        slab_offset = [0, 0]
        for i in range(0, self.numrows):
            
            if self.datatype == 'uint16':    
                if (i%100 == 0):
                    print('Mosaic row %i is being converted' % (i+1))
                dt = np.uint16
                data = stream.read(self.numcols*2)              
                imgdata = np.frombuffer(data, dtype=dt, count=self.numcols)
                imgdata = np.reshape(imgdata, (1, self.numcols), order='A')
                slab_offset = [i, 0]
                self.nxinstrument['sample']['data'].put(imgdata, slab_offset, 
                                                        refresh=False)
                self.nxinstrument['sample']['data'].write()
     
            elif self.datatype == 'float':  
                if (i%100 == 0):
                    print('Mosaic row %i is being converted' % (i+1))
                dt = np.float          
                data = stream.read(self.numcols*4)                      
                imgdata = np.frombuffer(data, dtype=dt, count=self.numcols)
                imgdata = np.reshape(imgdata, (1, self.numcols), order='A')
                slab_offset = [i, 0]
                self.nxinstrument['sample']['data'].put(imgdata, slab_offset, 
                                                        refresh=False)
                self.nxinstrument['sample']['data'].write()

            else:                            
                print "Wrong data type"
                return
           
        self.nxdata['data'] = nxs.NXlink(
                                    target=self.nxinstrument['sample']['data'], 
                                    group=self.nxdata)
        self.nxdata['data'].write()
        print ("Mosaic image data conversion to NeXus HDF5 has been done.\n")

        #### FF Data
        if (self.index_FF_file != -1):
            
            oleFF = OleFileIO(self.mosaic_file_FF_xrm)
            print ("\nTrying to convert FF xrm image to NeXus HDF5.\n")
            
            self.nxbright = nxs.NXgroup(name= 'bright_field')
            self.nxinstrument.insert(self.nxbright)
            self.nxbright.write() 
            # Mosaic FF data image

                       
            img_string = "ImageData1/Image1"
            stream = oleFF.openstream(img_string)        
            for i in range(0, self.nSampleFramesFF):
                
                if self.datatypeFF == 'uint16':    
                    dt = np.uint16
                    data = stream.read() 
                    struct_fmt = "<{0:10}H".format(
                                            self.numrowsFF*self.numcolsFF)
                    imgdata = struct.unpack(struct_fmt, data)
                    
                    imgdataFF = np.reshape(imgdata,     
                                    (self.numrowsFF, self.numcolsFF), order='A')
                    self.nxinstrument['bright_field']['data'] = nxs.NXfield(
                                        name='data', value = imgdataFF, 
                                        dtype=self.datatypeFF, 
                                        shape=[self.numrowsFF, self.numcolsFF])
                    FF_data = self.nxinstrument['bright_field']['data']
                    FF_data.attrs['Data Type']=self.datatypeFF 
                    FF_data.attrs['Number of images']=self.nSampleFramesFF
                    FF_data.attrs['Image Height']=self.numrowsFF
                    FF_data.attrs['Image Width']=self.numcolsFF
                    FF_data.write()            
                    print("FF image converted")
                    
                elif self.datatypeFF == 'float':  
                    dt = np.float          
                    data = stream.read()  
                    struct_fmt = "<{0:10}f".format(
                            self.numrowsFF*self.numcolsFF)
                    imgdata = struct.unpack(struct_fmt, data)
                    
                    imgdataFF = np.reshape(imgdata, 
                                    (self.numrowsFF, self.numcolsFF), order='A')
                    self.nxinstrument['bright_field']['data'] = nxs.NXfield(
                        name='data', value = imgdataFF, dtype='float' , 
                        shape=[self.numrowsFF, self.numcolsFF])
                    FF_data = self.nxinstrument['bright_field']['data']
                    FF_data.attrs['Data Type']=self.datatypeFF 
                    FF_data.attrs['Number of images']=self.nSampleFramesFF
                    FF_data.attrs['Image Height']=self.numrowsFF
                    FF_data.attrs['Image Width']=self.numcolsFF
                    FF_data.write()           
                    print("FF image converted")
                       
                else:                            
                    print "Wrong FF data type"
                    return
                      
            self.nxdata['data'] = nxs.NXlink(
                            target=self.nxinstrument['bright_field']['data'], 
                            group=self.nxdata)
            self.nxdata['data'].write()
        
            oleFF.close()    
            print ("Mosaic FF image data conversion to NeXus HDF5 " + 
                   "has been done.\n")
            return


