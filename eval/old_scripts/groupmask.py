from nipype.pipeline.engine import Node, MapNode, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.afni as afni
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.ants as ants
from nipype.utils.filemanip import filename_to_list
import nipype.interfaces.c3 as c3
import os


epimask = Workflow(name='epimask')


# inputnode
inputnode=Node(util.IdentityInterface(fields=['lin_mean_norm',
                                              'nonlin_mean_norm',
                                              'fmap_mean_norm',
                                              'topup_mean_norm']),
               name='inputnode')

# outputnode                                 
outputnode=Node(util.IdentityInterface(fields=['lin_automask',
                                               'nonlin_automask',
                                               'fmap_automask',
                                               'topup_automask'
                                               ]),
                name='outputnode')


# calculate automasks
lin_automask = Node(interface=afni.Automask(outputtype='NIFTI_GZ',
                                   clfrac = 0.6), 
                    name='lin_automask')

nonlin_automask = Node(interface=afni.Automask(outputtype='NIFTI_GZ',
                                   clfrac = 0.6), 
                    name='nonlin_automask')

# fmap_automask = Node(interface=afni.Automask(outputtype='NIFTI_GZ',
#                                    clfrac = 0.6), 
#                     name='fmap_automask')
# 
# topup_automask = Node(interface=afni.Automask(outputtype='NIFTI_GZ',
#                                    clfrac = 0.6), 
#                     name='topup_automask')


epimask.connect([(inputnode, lin_automask, [('lin_mean_norm','in_file')]),
                (inputnode, nonlin_automask, [('nonlin_mean_norm','in_file')]),
#                 (inputnode, fmap_automask, [('fmap_mean_norm','in_file')]),
#                 (inputnode, topup_automask, [('topup_mean_norm','in_file')]),
                (lin_automask, outputnode, [('out_file', 'lin_automask')]),
                (nonlin_automask, outputnode, [('out_file', 'nonlin_automask')]),
#                 (fmap_automask, outputnode, [('out_file', 'fmap_automask')]),
#                 (topup_automask, outputnode, [('out_file', 'topup_automask')]),
                ])


##### in and output ############

epimask.base_dir='/scr/kansas1/huntenburg/'
#topup.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir='/scr/jessica2/Schaare/LEMON/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=['LEMON001']
# subjects=[]
# f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
# for line in f:
#     subjects.append(line.strip())


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# select files
templates={'lin_mean_norm':'preprocessed/{subject_id}/coreg/lin_mean_norm.nii.gz',
           'nonlin_mean_norm':'preprocessed/{subject_id}/nonlin_coreg/nonlin_mean_norm.nii.gz',
#            'fmap_mean_norm':'preprocessed/{subject_id}/fieldmap_coreg/fmap_mean_norm.nii.gz',
#            'topup_mean_norm':'preprocessed/{subject_id}/topup_coreg/topup_mean_norm.nii.gz',
           }

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

#sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')
 
# connect to core workflow 
epimask.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
               (selectfiles, inputnode, [('lin_mean_norm', 'lin_mean_norm'),
                                         ('nonlin_mean_norm', 'nonlin_mean_norm'),
#                                          ('fmap_mean_norm', 'fmap_mean_norm'),
#                                          ('topup_mean_norm', 'topup_mean_norm')
                                         ]),
               (infosource, sink, [('subject_id', 'container')]),
               (outputnode, sink, [('lin_automask', 'coreg.@automask'),
                                   ('nonlin_automask', 'nonlin_coreg.@automask'),
#                                    ('fmap_automask', 'fmap_coreg.@automask'),
#                                    ('topup_automask', 'topup_coreg.@automask')
                                   ])                
               ])

epimask.run()