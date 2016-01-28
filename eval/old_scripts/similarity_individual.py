from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.fsl as fsl
import nipype.interfaces.nipy.utils as nutil
import nipype.interfaces.utility as util
from nipype.interfaces import Function
import nipype.interfaces.io as nio
import nipype.interfaces.afni as afni



similarity=Workflow(name='similarity')

# inputnode
inputnode=Node(util.IdentityInterface(fields=['anat_brain',
                                              'lin_mean_coreg',
                                              'nonlin_mean_coreg',
                                              'fmap_mean_coreg',
                                              'topup_mean_coreg'
                                              ]),
               name='inputnode')


# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['textfile']),
                name='outputnode')


# creating brainmask
brainmask = Node(fsl.maths.MathsCommand(args='-bin -fillh'),
                 name='fmap_mask')

similarity.connect([(inputnode, brainmask, [('anat_brain', 'in_file')])
                 ])

# # resampling brainmask and all means
# resamp_brain = Node(interface=afni.Resample(outputtype='NIFTI_GZ',
#                                  voxel_size = (3,3,3)),
#               name = 'resample_brain')
# similarity.connect([(inputnode, resamp_brain, [('anat_brain', 'in_file')])])
# 
# resamp_mask = Node(interface=afni.Resample(outputtype='NIFTI_GZ',
#                                  voxel_size = (3,3,3),),
#               name = 'resample_mask')
# similarity.connect([(brainmask, resamp_mask, [('out_file', 'in_file')])
#                     ])
# 
# resamp_lin = Node(interface=afni.Resample(outputtype='NIFTI_GZ',
#                                  voxel_size = (3,3,3)),
#               name = 'resample_lin')
# similarity.connect([(inputnode, resamp_lin, [('lin_mean_coreg', 'in_file')]),
#                     (resamp_brain, resamp_lin, [('out_file', 'master')])
#                     ])
# 
# resamp_nonlin = Node(interface=afni.Resample(outputtype='NIFTI_GZ',
#                                  voxel_size = (3,3,3)),
#               name = 'resample_nonlin')
# similarity.connect([(inputnode, resamp_nonlin, [('nonlin_mean_coreg', 'in_file')]),
#                     (resamp_brain, resamp_nonlin, [('out_file', 'master')])
#                     ])
# 
# resamp_fmap = Node(interface=afni.Resample(outputtype='NIFTI_GZ',
#                                  voxel_size = (3,3,3)),
#               name = 'resample_fmap')
# similarity.connect([(inputnode, resamp_nonlin, [('nonlin_mean_coreg', 'in_file')]),
#                     (resamp_brain, resamp_nonlin, [('out_file', 'master')])
#                     ])




# similarity linear coreg
lin_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_lin',
                  iterfield=['metric'])
lin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

similarity.connect([(inputnode, lin_sim, [('anat_brain', 'volume1'),
                                          ('lin_mean_coreg', 'volume2')]),
                    (brainmask, lin_sim, [('out_file', 'mask1'),
                                          ('out_file', 'mask2')])
                    ])

#similarity nonlinear coreg
nonlin_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_nonlin',
                  iterfield=['metric'])
nonlin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

similarity.connect([(inputnode, nonlin_sim, [('anat_brain', 'volume1'),
                                             ('nonlin_mean_coreg', 'volume2')]),
                    (brainmask, nonlin_sim, [('out_file', 'mask1'),
                                             ('out_file', 'mask2')])
                    ])

#similarity fmap
fmap_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_fmap',
                  iterfield=['metric'])
fmap_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

similarity.connect([(inputnode, fmap_sim, [('anat_brain', 'volume1'),
                                             ('fmap_mean_coreg', 'volume2')]),
                    (brainmask, fmap_sim, [('out_file', 'mask1'),
                                           ('out_file', 'mask2')])
                    ])

#similarity topup
topup_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_topup',
                  iterfield=['metric'])
topup_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
 
similarity.connect([(inputnode, topup_sim, [('anat_brain', 'volume1'),
                                             ('topup_mean_coreg', 'volume2')]),
                    (brainmask, topup_sim, [('out_file', 'mask1'),
                                            ('out_file', 'mask2')])
                    ])



# write values to file
def write_text(lin_metrics, nonlin_metrics, fmap_metrics, topup_metrics):
    import numpy as np
    import os
    lin_array = np.array(lin_metrics)
    lin_array=lin_array.reshape(np.size(lin_array),1)
    nonlin_array = np.array(nonlin_metrics)
    nonlin_array=nonlin_array.reshape(np.size(nonlin_array),1)
    fmap_array = np.array(fmap_metrics)
    fmap_array=fmap_array.reshape(np.size(fmap_array),1)
    topup_array = np.array(topup_metrics)
    topup_array=topup_array.reshape(np.size(topup_array),1)
    
    metrics=np.concatenate((lin_array, nonlin_array, fmap_array, topup_array),axis=1)
    metrics_file = 'brain_metrics.txt'
    np.savetxt(metrics_file, metrics, delimiter=' ', fmt='%f')
    return os.path.abspath('brain_metrics.txt')
    

write_txt = Node(interface=Function(input_names=['lin_metrics', 'nonlin_metrics', 'fmap_metrics', 'topup_metrics'],
                                  output_names=['txtfile'],
                                  function=write_text),
              name='write_file')

similarity.connect([(lin_sim, write_txt, [('similarity', 'lin_metrics')]),
                    (nonlin_sim, write_txt, [('similarity', 'nonlin_metrics')]),
                    (fmap_sim, write_txt, [('similarity', 'fmap_metrics')]),
                    (topup_sim, write_txt, [('similarity', 'topup_metrics')]),
                    (write_txt, outputnode, [('txtfile', 'textfile')])
                    ])

# in and out
similarity.base_dir='/scr/kansas1/huntenburg/'
similarity.config['execution']={'remove_unnecessary_outputs': 'False'}
out_dir='/scr/jessica2/Schaare/LEMON/preprocessed/'
data_dir='/scr/jessica2/Schaare/LEMON/preprocessed/'
#subjects=['LEMON001']
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
for line in f:
    subjects.append(line.strip())
subjects.remove('LEMON027')


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)


# select files
templates={'anat_brain': '{subject_id}/freesurfer_anatomy/brain_out.nii.gz',
           'lin_mean_coreg':'{subject_id}/coreg/lin_mean_coreg.nii.gz',
           'nonlin_mean_coreg':'{subject_id}/nonlin_coreg/nonlin_mean_coreg.nii.gz',
           'fmap_mean_coreg':'{subject_id}/fieldmap_coreg/fmap_mean_coreg.nii.gz',
           'topup_mean_coreg':'{subject_id}/topup_coreg/topup_mean_coreg.nii.gz'
}


selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")


sink = Node(nio.DataSink(base_directory=out_dir,
                            parameterization=False), 
               name='sink')

similarity.connect([(outputnode, sink,[('textfile', 'similarity.@txtfile')]),
                    (infosource, selectfiles, [('subject_id', 'subject_id')]),
                    (infosource, sink, [('subject_id', 'container')]),
                    (selectfiles, inputnode, [('anat_brain', 'anat_brain'),
                                              ('lin_mean_coreg', 'lin_mean_coreg'),
                                              ('nonlin_mean_coreg', 'nonlin_mean_coreg'),
                                              ('fmap_mean_coreg', 'fmap_mean_coreg'),
                                              ('topup_mean_coreg', 'topup_mean_coreg')
                                              ])
                    ])


similarity.run(plugin='CondorDAGMan')


