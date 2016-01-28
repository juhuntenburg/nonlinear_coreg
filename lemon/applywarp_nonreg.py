from nipype.pipeline.engine import Node, Workflow
from nipype.interfaces import Function
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.ants as ants
import os

'''
=============================================================================
CHECK WHICH EPI_T1_NONLINEAR BRANCH YOU ARE ON AND ADAPT THE VERSION VARIABLE
=============================================================================
'''
version='version_19'



# workflow
applywarp_nonlinear = Workflow(name='applywarp_nonlinear')

# set up workflow, in- and output
applywarp_nonlinear.base_dir='/scr/kansas1/huntenburg/nonlinear/'+version+'/working_dir/'
data_dir='/scr/jessica2/Schaare/LEMON/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
applywarp_nonlinear.config['execution']['crashdump_dir'] = applywarp_nonlinear.base_dir + "/crash_files"

# reading subjects from file
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
for line in f:
    subjects.append(line.strip())
subjects=['LEMON001']

# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# select files
templates={'epi_coreg':'preprocessed/{subject_id}/nonlin_coreg_'+version+'/nonlin_mean_coreg.nii.gz',
           'mni':'MNI152_T1_1mm.nii.gz',
           'norm_lin':'preprocessed/{subject_id}/normalization/transform0GenericAffine.mat',
           'norm_warp':'preprocessed/{subject_id}/normalization/transform1Warp.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")


# inputnode
inputnode=Node(util.IdentityInterface(fields=['epi_coreg',
                                              'mni',
                                              'norm_lin',
                                              'norm_warp']),
               name='inputnode')


# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['nonlin_mean_fullwarped',
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
 
applywarp_nonlinear.connect([(inputnode, transformlist, [('norm_lin', 'trans2'),
                                                      ('norm_warp', 'trans1')])
                          ])
        
        
# apply warp to coregistered mean        
applytransform = Node(ants.ApplyTransforms(dimension=3,
                                           output_image='nonlin_mean_norm.nii.gz',
                                           interpolation = 'BSpline'),
                      'applytransform')
 
applywarp_nonlinear.connect([(inputnode, applytransform, [('epi_coreg', 'input_image')]),
                          (inputnode, applytransform, [('mni', 'reference_image')]),
                          (transformlist, applytransform, [('transformlist', 'transforms')]),
                          (applytransform, outputnode, [('output_image', 'nonlin_mean_fullwarped')])
                          ])


# sink to store data
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')

# connections
applywarp_nonlinear.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
                          (infosource, sink, [('subject_id', 'container')]),
                          (selectfiles, inputnode, [('epi_coreg', 'epi_coreg'),
                                                    ('mni', 'mni'),
                                                    ('norm_lin', 'norm_lin'),
                                                    ('norm_warp', 'norm_warp')]),
                          (outputnode, sink, [('nonlin_mean_fullwarped', 'nonlin_coreg_'+version+'.@nonlin_mean_fullwarped'),])
                ])


applywarp_nonlinear.run(plugin='CondorDAGMan')