from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.fsl as fsl
import nipype.interfaces.nipy.utils as nutil
import nipype.interfaces.utility as util
from nipype.interfaces import Function
import nipype.interfaces.io as nio
import nipype.interfaces.afni as afni



similarity=Workflow(name='similarity_ofc_mni')

# inputnode
inputnode=Node(util.IdentityInterface(fields=['mni',
                                              'mni_ofc_mask',
                                              'lin_mean_norm',
                                              'nonlin_mean_norm',
                                              'fmap_mean_norm',
                                              'topup_mean_norm'
                                              ]),
               name='inputnode')


# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['textfile']),
                name='outputnode')


# creating brainmask
brainmask = Node(fsl.maths.MathsCommand(args='-bin -fillh'),
                 name='brainmask')

similarity.connect([(inputnode, brainmask, [('mni_ofc_mask', 'in_file')])
                 ])

# similarity linear coreg
lin_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_lin',
                  iterfield=['metric'])
lin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

similarity.connect([(inputnode, lin_sim, [('mni', 'volume1'),
                                          ('lin_mean_norm', 'volume2')]),
                    (brainmask, lin_sim, [('out_file', 'mask1'),
                                          ('out_file', 'mask2')])
                    ])

#similarity nonlinear coreg
nonlin_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_nonlin',
                  iterfield=['metric'])
nonlin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

similarity.connect([(inputnode, nonlin_sim, [('mni', 'volume1'),
                                             ('nonlin_mean_norm', 'volume2')]),
                    (brainmask, nonlin_sim, [('out_file', 'mask1'),
                                             ('out_file', 'mask2')])
                    ])

#similarity fmap
fmap_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_fmap',
                  iterfield=['metric'])
fmap_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

similarity.connect([(inputnode, fmap_sim, [('mni', 'volume1'),
                                             ('fmap_mean_norm', 'volume2')]),
                    (brainmask, fmap_sim, [('out_file', 'mask1'),
                                           ('out_file', 'mask2')])
                    ])

#similarity topup
topup_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_topup',
                  iterfield=['metric'])
topup_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
 
similarity.connect([(inputnode, topup_sim, [('mni', 'volume1'),
                                             ('topup_mean_norm', 'volume2')]),
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
    metrics_file = 'mni_ofc_metrics.txt'
    np.savetxt(metrics_file, metrics, delimiter=' ', fmt='%f')
    return os.path.abspath('mni_ofc_metrics.txt')
    

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
out_dir='/scr/jessica2/Schaare/LEMON/preprocessed/'
data_dir='/scr/jessica2/Schaare/LEMON/'
# subjects=['LEMON001']
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
for line in f:
    subjects.append(line.strip())
subjects.remove('LEMON027')
subjects.remove('LEMON007')


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)


# select files
templates={'mni': 'MNI152_T1_1mm_brain.nii.gz',
           'mni_ofc_mask': 'frontal_orbital_thr_25.nii.gz',
           'lin_mean_norm':'preprocessed/{subject_id}/coreg/lin_mean_norm.nii.gz',
           'nonlin_mean_norm':'preprocessed/{subject_id}/nonlin_coreg/nonlin_mean_norm.nii.gz',
           'fmap_mean_norm':'preprocessed/{subject_id}/fieldmap_coreg/fmap_mean_norm.nii.gz',
           'topup_mean_norm':'preprocessed/{subject_id}/topup_coreg/topup_mean_norm.nii.gz'
}


selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")


sink = Node(nio.DataSink(base_directory=out_dir,
                            parameterization=False), 
               name='sink')

similarity.connect([(outputnode, sink,[('textfile', 'similarity.@mni_txtfile')]),
                    (infosource, selectfiles, [('subject_id', 'subject_id')]),
                    (infosource, sink, [('subject_id', 'container')]),
                    (selectfiles, inputnode, [('mni', 'mni'),
                                              ('mni_ofc_mask', 'mni_ofc_mask'),
                                              ('lin_mean_norm', 'lin_mean_norm'),
                                              ('nonlin_mean_norm', 'nonlin_mean_norm'),
                                              ('fmap_mean_norm', 'fmap_mean_norm'),
                                              ('topup_mean_norm', 'topup_mean_norm')
                                              ])
                    ])


similarity.run(plugin='CondorDAGMan')


