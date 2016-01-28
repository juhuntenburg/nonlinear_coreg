from nipype.pipeline.engine import Node, Workflow
from nipype.interfaces import Function
from nipype.utils.filemanip import filename_to_list
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.ants as ants
import nipype.interfaces.c3 as c3
import nipype.interfaces.freesurfer as fs
from epi_t1_nonlinear import create_epi_t1_nonlinear_pipeline
import os

'''
=============================================================================
CHECK WHICH EPI_T1_NONLINEAR BRANCH YOU ARE ON AND ADAPT THE VERSION VARIABLE
=============================================================================
'''

# version
version='version_5'

'''beware that if additional inputs to epi_t1_nonlinear.py are necessary this needs to
be specified in the two if-statements below '''




# inputs and directories
nonreg = Workflow(name='nonreg')
nonreg.base_dir='/scr/kansas1/huntenburg/nonlinear/'+version+'/working_dir/'
data_dir='/scr/jessica2/Schaare/LEMON/'
fs_subjects_dir='/scr/jessica2/Schaare/LEMON/freesurfer/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
#nonreg.config['execution']={'remove_unnecessary_outputs': 'False'}
nonreg.config['execution']['crashdump_dir'] = nonreg.base_dir + "/crash_files"

if version == 'version_3' or version == 'version_4' or version == 'version_6' or version == 'version_7' or version == 'version_13' or version == 'version_14' or version == 'version_15' or version == 'version_18' or version == 'version_19' :
    fmap_mask='/scr/kansas1/huntenburg/nonlinear/fmap_mask/fmap_mask_1922_fillh_blur4_bin01_masked.nii.gz'


# reading subjects from file
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
for line in f:
    subjects.append(line.strip())
    
subjects=['LEMON001']


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id','fs_subjects_dir']), 
                  name='infosource')
infosource.inputs.fs_subjects_dir=fs_subjects_dir
infosource.iterables=('subject_id', subjects)

# select files
templates={'realigned_epi':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'anat_head':'preprocessed/{subject_id}/freesurfer_anatomy/T1_out.nii.gz',
           'norm_lin':'preprocessed/{subject_id}/normalization/transform0GenericAffine.mat',
           'norm_invwarp':'preprocessed/{subject_id}/normalization/transform1InverseWarp.nii.gz'
           }

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# create epi to t1 nonlinear core workflow
nonreg_core= create_epi_t1_nonlinear_pipeline('nonreg_core')


# connect to core workflow 
nonreg.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
                (infosource, nonreg_core, [('subject_id', 'inputnode.fs_subject_id'),
                                           ('fs_subjects_dir', 'inputnode.fs_subjects_dir')]),
                (selectfiles, nonreg_core, [('realigned_epi', 'inputnode.realigned_epi')]),
                ])


if version == 'version_3' or version == 'version_4' or version == 'version_6' or version == 'version_7' or version == 'version_13' or version == 'version_14' or version == 'version_15' or version == 'version_18' or version == 'version_19':
    nonreg.connect([(selectfiles, nonreg_core, [('norm_lin', 'inputnode.norm_lin'),
                                                ('norm_invwarp', 'inputnode.norm_invwarp')])])
    nonreg_core.inputs.inputnode.fmap_mask = fmap_mask


#make list from transforms
def makelist(string1, string2):
    transformlist=[string1, string2]
    return transformlist
   
transformlist = Node(interface=Function(input_names=['string1', 'string2'],
                                        output_names=['transformlist'],
                                        function=makelist),
                     name='transformlist')
  
nonreg.connect([(nonreg_core, transformlist, [('outputnode.nonlin_epi2anat', 'string2'),
                                              ('outputnode.lin_anat2epi', 'string1')
                                              ])
                 ])
                
#apply warp 
applytransform = Node(ants.ApplyTransforms(dimension=3,
                                                   output_image='nonlin_mean_coreg.nii.gz',
                                                   invert_transform_flags=[True,False],
                                                   interpolation = 'BSpline'),
                      'applytransform')
     
nonreg.connect([(nonreg_core, applytransform, [('inputnode.realigned_epi', 'input_image')]),
                (selectfiles, applytransform, [('anat_head', 'reference_image')]),
                (transformlist, applytransform, [('transformlist', 'transforms')]),
                ])



#sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                            parameterization=False), 
               name='sink')
  
nonreg.connect([(infosource, sink, [('subject_id', 'container')]),
                (nonreg_core, sink, [('outputnode.lin_epi2anat', 'nonlin_coreg_'+version+'.@lin_epi2anat'),
                                     ('outputnode.lin_anat2epi', 'nonlin_coreg_'+version+'.@lin_anat2epi'),
                                     ('outputnode.nonlin_epi2anat', 'nonlin_coreg_'+version+'.@nonlin_epi2anat'),
                                     ('outputnode.nonlin_anat2epi', 'nonlin_coreg_'+version+'.@nonlin_anat2epi')]),
                (applytransform, sink, [('output_image', 'nonlin_coreg_'+version+'.@nonlin_mean_coreg')])
                ])


nonreg.run(plugin='CondorDAGMan')

