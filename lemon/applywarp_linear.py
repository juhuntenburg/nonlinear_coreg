from nipype.pipeline.engine import Node, Workflow
from nipype.interfaces import Function
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.ants as ants
import os


# workflow
applywarp_linear = Workflow(name='applywarp_linear')


# inputnode
inputnode=Node(util.IdentityInterface(fields=['epi_coreg',
                                              #'epi_moco_ts',
                                              'mni',
                                              #'moco_mats',
                                              #'coreg_lin_epi2anat',
                                              'norm_lin',
                                              'norm_warp']),
               name='inputnode')


# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['lin_mean_fullwarped',
                                               #'lin_ts_fullwarped'
                                               ]),
                name='outputnode')



# make list from transforms
def makelist(trans1, trans2):
    transformlist=[trans1, trans2]
    return transformlist
  
transformlist = Node(interface=Function(input_names=['trans1', 'trans2'],
                                        output_names=['transformlist'],
                                        function=makelist),
                     name='transformlist')
 
applywarp_linear.connect([(inputnode, transformlist, [('norm_lin', 'trans2'),
                                                      ('norm_warp', 'trans1')])
                          ])
        
        
# apply warp to coregistered mean        
applytransform = Node(ants.ApplyTransforms(dimension=3,
                                           output_image='lin_mean_norm.nii.gz',
                                           interpolation = 'BSpline'),
                      'applytransform')
 
applywarp_linear.connect([(inputnode, applytransform, [('epi_coreg', 'input_image')]),
                          (inputnode, applytransform, [('mni', 'reference_image')]),
                          (transformlist, applytransform, [('transformlist', 'transforms')]),
                          (applytransform, outputnode, [('output_image', 'lin_mean_fullwarped')])
                          ])
        

# apply warp to timeseries
# applytransform_ts = Node(ants.WarpTimeSeriesImageMultiTransform(dimension=4),
#                          name='applytransform_ts')
#    
#    
# applywarp_linear.connect([(inputnode, applytransform_ts, [('epi_moco_ts','input_image')]),
#                           (transformlist, applytransform_ts, [('transformlist', 'transformation_series')]),
#                           (inputnode, applytransform_ts, [('mni', 'reference_image')]),
#                           (applytransform_ts, outputnode, [('output_image','lin_ts_fullwarped')])
#                           ])


# set up workflow, in- and output
applywarp_linear.base_dir='/scr/kansas1/huntenburg/lemon_missing/working_dir/'
data_dir='/scr/jessica2/Schaare/LEMON/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
#applywarp_linear.config['execution']={'remove_unnecessary_outputs': 'False'}
applywarp_linear.config['execution']['crashdump_dir'] = applywarp_linear.base_dir + "/crash_files"

# reading subjects from file
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/missing_subjects.txt','r')
for line in f:
    subjects.append(line.strip())


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# select files
templates={'epi_coreg':'preprocessed/{subject_id}/coreg/lin_mean_coreg.nii.gz',
           #'epi_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           #'epi_moco_ts':'preprocessed/{subject_id}/motion_correction/rest_moco.nii.gz',
           #'moco_mats':'preprocessed/{subject_id}/motion_correction/MAT/*',
           'mni':'MNI152_T1_1mm.nii.gz',
           #'coreg_lin_epi2anat':'preprocessed/{subject_id}/coreg/lin_epi2anat_affine.txt',
           'norm_lin':'preprocessed/{subject_id}/normalization/transform0GenericAffine.mat',
           'norm_warp':'preprocessed/{subject_id}/normalization/transform1Warp.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# sink to store data
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')

# connect to core workflow 
applywarp_linear.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
                          (infosource, sink, [('subject_id', 'container')]),
                          (selectfiles, inputnode, [('epi_coreg', 'epi_coreg'),
                                                    #('epi_mean', 'epi_mean'),
                                                    #('epi_moco_ts', 'epi_moco_ts'),
                                                    #('moco_mats', 'moco_mats'),
                                                    ('mni', 'mni'),
                                                    #('coreg_lin_epi2anat', 'coreg_lin_epi2anat'),
                                                    ('norm_lin', 'norm_lin'),
                                                    ('norm_warp', 'norm_warp')]),
                          (outputnode, sink, [('lin_mean_fullwarped', 'coreg.@lin_mean_fullwarped'),
                                              #('lin_ts_fullwarped', 'coreg.@lin_ts_fullwarped')
                                              ])
                ])

applywarp_linear.run(plugin='CondorDAGMan')