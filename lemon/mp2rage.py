from nipype.pipeline.engine import Workflow, Node 
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
import os
from nipype.interfaces.mipav.developer import JistIntensityMp2rageMasking, MedicAlgorithmSPECTRE2010




#### core workflow ##################################################################################

# workflow
mp2rage = Workflow('mp2rage_litauen')

# inputnode 
inputnode=Node(util.IdentityInterface(fields=['inv2',
                                              'uni',
                                              't1map']),
           name='inputnode')

# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['uni_masked',
                                               'background_mask',
                                               'uni_stripped',
                                               'skullstrip_mask'
                                               ]),
            name='outputnode')

# remove background noise
background = Node(JistIntensityMp2rageMasking(outMasked=True,
                                        outMasked2=True,
                                        outSignal2=True), 
                  name='background')

# skullstrip
strip = Node(MedicAlgorithmSPECTRE2010(outStripped=True,
                                       outMask=True,
                                       outOriginal=True,
                                       inOutput='true',
                                       inFind='true',
                                       #maxMemoryUsage = 6000,
                                       #inMMC=4
                                       ), 
             name='strip')
strip.iterables=('inMMC',[2,4])

# connections
mp2rage.connect([(inputnode, background, [('inv2', 'inSecond'),
                                          ('t1map', 'inQuantitative'),
                                          ('uni', 'inT1weighted')]),
                 (background, strip, [('outMasked2','inInput')]),
                 (background, outputnode, [('outMasked2','uni_masked'),
                                           ('outMasked','t1map_masked'),
                                           ('outSignal2','background_mask')]),
                 (strip, outputnode, [('outStripped','uni_stripped'),
                                      ('outMask', 'skullstrip_mask'),
                                      ('outOriginal','uni_reoriented')])
                 ])


#### in and out ####################################################################################

#mp2rage.base_dir='/scr/ilz1/nonlinear_registration/lemon/testing/dicom_start/'
mp2rage.base_dir='/scr/kansas1/huntenburg/'
data_dir='/scr/litauen1/lsd/pilot_140521/dicoms/DL1T/'
#data_dir='/scr/ilz1/nonlinear_registration/lemon/testing/dicom_start/'
#data_dir = '/scr/jessica2/Schaare/LEMON/raw/'
#out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
#mp2rage.config['execution']={'remove_unnecessary_outputs': 'False'}
subjects=['LEMON064', 'LEMON065', 'LEMON096']
# subjects=os.listdir(data_dir)
# subjects.remove('LEMON025')
# subjects.remove('LEMON065')

#infosource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

#define templates and select files
# templates={'inv2':'{subject_id}/mp2rage/inv2.nii.gz',
#            't1map':'{subject_id}/mp2rage/t1.nii.gz',
#            'uni':'{subject_id}/mp2rage/uni.nii.gz'}

templates={'inv2':'013-mp2rage_p3_602B.nii.gz',
           't1map':'015-mp2rage_p3_602B.nii.gz',
           'uni':'016-mp2rage_p3_602B.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# sink to store files
# sink = Node(nio.DataSink(base_directory=out_dir,
#                           parameterization=False), 
#              name='sink')

# connect to core workflow
mp2rage.connect([#(infosource, selectfiles, [('subject_id', 'subject_id')]),
                 #(infosource, sink, [('subject_id', 'container')]),
                 (selectfiles, inputnode, [('inv2', 'inv2'),
                                           ('uni', 'uni'),
                                           ('t1map', 't1map')]),
#                 (outputnode, sink, [('uni_masked','background_masking.@uni_masked'),
#                                     ('t1map_masked','background_masking.@t1map_masked'),
#                                     ('background_mask','background_masking.@background_mask'),
#                                     ('uni_stripped','skullstrip.@uni_stripped'),
#                                     ('skullstrip_mask', 'skullstrip.@skullstrip_mask'),
#                                     ('uni_reoriented','skullstrip.@uni_reoriented')])
                      ])


#### run #########################################################################################

mp2rage.run()
#(plugin='MultiProc')
#(plugin='CondorDAGMan')
