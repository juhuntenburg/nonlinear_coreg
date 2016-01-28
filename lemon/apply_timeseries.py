from nipype.pipeline.engine import Node, Workflow
from nipype.interfaces import Function
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.ants as ants
import nipype.interfaces.fsl as fsl
from nipype.utils.filemanip import filename_to_list
import os

fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

# workflow
apply_ts = Workflow(name='nonlinear_timeseries')


# inputnode
inputnode=Node(util.IdentityInterface(fields=['moco_ts',
                                              'moco_mean',
                                              'anat_head',
                                              'lin_epi2anat_itk',
                                              'nonlin_anat2epi_itk',
                                              'nonlin_epi2anat_warp',
                                              'fmap_fullwarp',
                                              'topup_fullwarp']),
               name='inputnode')


# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['lin_ts',
                                               'nonlin_ts',
                                               'fmap_ts',
                                               'topup_ts'
                                               ]),
                name='outputnode')


# resample anatomy
resamp_anat = Node(fsl.FLIRT(apply_isoxfm=2.3),
                   name = 'resample_anat')
apply_ts.connect([(inputnode, resamp_anat, [('anat_head', 'in_file'),
                                            ('anat_head', 'reference'),
                                            ]),
                  ])



# linear
# lin_apply = Node(ants.ApplyTransforms(input_image_type=3,
#                                       output_image='lin_ts.nii.gz',
#                                       interpolation = 'BSpline'),
#                       'lin_apply')
#    
# apply_ts.connect([(inputnode, lin_apply, [('moco_ts', 'input_image'),
#                                           #('anat_head', 'reference_image'),
#                                           (('lin_epi2anat_itk', filename_to_list), 'transforms')]),
#                   (resamp_anat, lin_apply, [('out_file', 'reference_image')]),
#                   (lin_apply, outputnode, [('output_image', 'lin_ts')])
#                   ])

# nonlinear
def makelist(string1, string2):
    transformlist=[string1, string2]
    return transformlist
     
transformlist = Node(interface=Function(input_names=['string1', 'string2'],
                                        output_names=['transformlist'],
                                        function=makelist),
                     name='transformlist')
    
apply_ts.connect([(inputnode, transformlist, [('nonlin_epi2anat_warp', 'string2'),
                                              ('nonlin_anat2epi_itk', 'string1')
                                              ])
                 ])
  
nonlin_apply = Node(ants.ApplyTransforms(input_image_type=3,
                                         output_image='nonlin_ts.nii.gz',
                                         invert_transform_flags=[True,False],
                                         interpolation = 'BSpline'),
                    'nonlin_apply')
nonlin_apply.plugin_args={'initial_specs': 'request_memory = 22000'}
  
apply_ts.connect([(inputnode, nonlin_apply, [('moco_ts', 'input_image'),
                                             #('anat_head', 'reference_image')
                                               ]),
                  (resamp_anat, nonlin_apply, [('out_file', 'reference_image')]),
                  (transformlist, nonlin_apply, [('transformlist', 'transforms')]),
                  (nonlin_apply, outputnode, [('output_image', 'nonlin_ts')])
                  ])

# set up workflow, in- and output
apply_ts.base_dir='/scr/kansas1/huntenburg/'
data_dir='/scr/jessica2/Schaare/LEMON/'
#out_dir = '/scr/kansas1/huntenburg/timeseries/'
#applywarp_linear.config['execution']={'remove_unnecessary_outputs': 'False'}
apply_ts.config['execution']['crashdump_dir'] = apply_ts.base_dir + "/crash_files"



# reading subjects from file
#subjects=['LEMON003']
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
for line in f:
    subjects.append(line.strip())
subjects.remove('LEMON007')
subjects.remove('LEMON027')
subjects.remove('LEMON003')

# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# select files
templates={'moco_ts':'preprocessed/{subject_id}/motion_correction/rest_moco.nii.gz',
           'moco_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'anat_head':'preprocessed/{subject_id}/freesurfer_anatomy/T1_out.nii.gz',
           'lin_epi2anat_itk':'preprocessed/{subject_id}/coreg/lin_epi2anat_affine.txt',
           'nonlin_anat2epi_itk':'preprocessed/{subject_id}/nonlin_coreg/transform0GenericAffine.mat',
           'nonlin_epi2anat_warp':'preprocessed/{subject_id}/nonlin_coreg/transform1InverseWarp.nii.gz',
           #'fmap_fullwarp':'preprocessed/{subject_id}/fieldmap_coreg/',
           #'topup_fullwarp':'preprocessed/{subject_id}/topup_coreg/'
           }

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# sink to store data
# sink = Node(nio.DataSink(base_directory=out_dir,
#                           parameterization=False), 
#              name='sink')

# connect to core workflow 
apply_ts.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
                  #(infosource, sink, [('subject_id', 'container')]),
                  (selectfiles, inputnode, [('moco_ts', 'moco_ts'),
                                            ('moco_mean','moco_mean'),
                                            ('anat_head', 'anat_head'),
                                            ('lin_epi2anat_itk', 'lin_epi2anat_itk'),
                                            ('nonlin_anat2epi_itk', 'nonlin_anat2epi_itk'),
                                            ('nonlin_epi2anat_warp', 'nonlin_epi2anat_warp'),
                                            #('fmap_fullwarp','fmap_fullwarp'),
                                            #('topup_fullwarp','topup_fullwarp')
                                            ]),
#                 (outputnode, sink, [('lin_ts', '@lin_ts'),
#                                     ('nonlin_ts', '@nonlin_ts'),
#                                    ('fmap_ts', '@fmap_ts'),
#                                    ('topup_ts', '@topup_ts')
#                                    ])
                ])

apply_ts.run(plugin='CondorDAGMan')