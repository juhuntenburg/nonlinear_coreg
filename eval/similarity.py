from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.nipy.utils as nutil
import nipype.interfaces.utility as util
from nipype.interfaces import Function
import nipype.interfaces.afni as afni


def create_similarity_pipeline(name):

    similarity=Workflow(name=name)

    # inputnode
    inputnode=Node(util.IdentityInterface(fields=['anat_brain',
                                                  'mask',
                                                  'lin_mean',
                                                  'nonlin_mean',
                                                  'fmap_mean',
                                                  'topup_mean',
                                                  'filename'
                                                  ]),
                   name='inputnode')
    
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['textfile']),
                    name='outputnode')

    
    # resample all means to make sure they have the same resolution as reference anatomy 
    resamp_mask = Node(afni.Resample(outputtype='NIFTI_GZ'), name='resample_mask')
    resamp_lin = resamp_mask.clone(name = 'resample_lin')
    resamp_nonlin = resamp_mask.clone(name='resample_nonlin')
    resamp_fmap = resamp_mask.clone(name='resample_fmap')
    resamp_topup = resamp_mask.clone(name='resample_topup')
    
    similarity.connect([(inputnode, resamp_mask, [('mask', 'in_file'),
                                                 ('anat_brain', 'master')]),
                        (inputnode, resamp_lin, [('lin_mean', 'in_file'),
                                                 ('anat_brain', 'master')]),
                        (inputnode, resamp_nonlin, [('nonlin_mean', 'in_file'),
                                                 ('anat_brain', 'master')]),
                        (inputnode, resamp_fmap, [('fmap_mean', 'in_file'),
                                                 ('anat_brain', 'master')]),
                        (inputnode, resamp_topup, [('topup_mean', 'in_file'),
                                                 ('anat_brain', 'master')]),
                        ])
    
    # calculate similarity (all possible metrics) for each methods to mni
    lin_sim = MapNode(interface = nutil.Similarity(),
                      name = 'similarity_lin',
                      iterfield=['metric'])
    lin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
    
    nonlin_sim = lin_sim.clone(name='similarity_nonlin')
    nonlin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
    fmap_sim = lin_sim.clone(name='similarity_fmap')
    fmap_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
    topup_sim = lin_sim.clone(name='similarity_topup')
    topup_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
    
    similarity.connect([(inputnode, lin_sim, [('anat_brain', 'volume1')]),
                        (resamp_lin, lin_sim, [('out_file', 'volume2')]),
                        (resamp_mask, lin_sim, [('out_file', 'mask1'),
                                               ('out_file', 'mask2')]),
                        (inputnode, nonlin_sim, [('anat_brain', 'volume1')]),
                        (resamp_nonlin, nonlin_sim, [('out_file', 'volume2')]),
                        (resamp_mask, nonlin_sim, [('out_file', 'mask1'),
                                                   ('out_file', 'mask2')]),
                        (inputnode, fmap_sim, [('anat_brain', 'volume1')]),
                        (resamp_fmap, fmap_sim, [('out_file', 'volume2')]),
                        (resamp_mask, fmap_sim, [('out_file', 'mask1'),
                                               ('out_file', 'mask2')]),
                        (inputnode, topup_sim, [('anat_brain', 'volume1')]),
                        (resamp_topup, topup_sim, [('out_file', 'volume2')]),
                        (resamp_mask, topup_sim, [('out_file', 'mask1'),
                                               ('out_file', 'mask2')])
                        ])
    
    
    # write values to one text file per subject
    def write_text(lin_metrics, nonlin_metrics, fmap_metrics, topup_metrics, filename):
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
        metrics_file = filename
        np.savetxt(metrics_file, metrics, delimiter=' ', fmt='%f')
        return os.path.abspath(filename)
    
    
    write_txt = Node(interface=Function(input_names=['lin_metrics', 'nonlin_metrics', 'fmap_metrics', 'topup_metrics', 'filename'],
                                      output_names=['txtfile'],
                                      function=write_text),
                  name='write_file')
    
    similarity.connect([(inputnode, write_txt, [('filename', 'filename')]),
                        (lin_sim, write_txt, [('similarity', 'lin_metrics')]),
                        (nonlin_sim, write_txt, [('similarity', 'nonlin_metrics')]),
                        (fmap_sim, write_txt, [('similarity', 'fmap_metrics')]),
                        (topup_sim, write_txt, [('similarity', 'topup_metrics')]),
                        (write_txt, outputnode, [('txtfile', 'textfile')])
                        ])
    
    
    return similarity