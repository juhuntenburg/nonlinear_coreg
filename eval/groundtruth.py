# see readme file for how to get the simulated data
#import libraries
from nipype.pipeline.engine import MapNode, Node, Workflow
from nipype.interfaces import Function
from nipype.utils.filemanip import filename_to_list
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.nipy.utils as nutil
import nipype.interfaces.fsl as fsl
import nipype.interfaces.ants as ants
import nipype.interfaces.c3 as c3
import nipype.interfaces.freesurfer as fs
from epi_t1_nonlinear import create_epi_t1_nonlinear_pipeline
import os
from correlation import calc_img_spearmanr

def create_groundtruth_pipeline(name):

    # workflow
    groundtruth = Workflow(name=name)
    
    # inputnode
    inputnode=Node(util.IdentityInterface(fields=['fmap_mask',
                                                  'anat_head',
                                                  'anat_brain',
                                                  'anat_brain_mask',
                                                  'epi',
                                                  'freesurfer_dir',
                                                  'freesurfer_id',
                                                  'norm_lin',
                                                  'norm_invwarp',
                                                  'nonreg_mask']),
                   name='inputnode')
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['lin_coreg', 
                                                   'nonlin_coreg',
                                                   'nonlin_field',
                                                   'nonlin_field_masked',
                                                   'corr_txtfile',
                                                   'sim_txtfile']),
                    name='outputnode')

      
    # epi to t1 nonlinear core workflow
    nonreg= create_epi_t1_nonlinear_pipeline('nonreg')
    groundtruth.connect([(inputnode, nonreg, [('epi', 'inputnode.realigned_epi'),
                                              ('freesurfer_dir', 'inputnode.fs_subjects_dir'),
                                              ('freesurfer_id', 'inputnode.fs_subject_id')])])
    
    groundtruth.connect([(inputnode, nonreg, [('norm_lin', 'inputnode.norm_lin'),
                                                  ('norm_invwarp', 'inputnode.norm_invwarp'),
                                                  ('nonreg_mask', 'inputnode.fmap_mask')])])
    
    #make list from transforms
    def makelist(string1, string2):
        transformlist=[string1, string2]
        return transformlist
       
    transformlist = Node(interface=Function(input_names=['string1', 'string2'],output_names=['transformlist'],
                                            function=makelist),name='transformlist')
      
    groundtruth.connect([(nonreg, transformlist, [('outputnode.nonlin_epi2anat', 'string2'),
                                                 ('outputnode.lin_anat2epi', 'string1')])])
                    
    # apply linear part of warp
    applylin = Node(ants.ApplyTransforms(dimension=3,
                                         output_image='lin_coreg.nii.gz',
                                         invert_transform_flags=[True]
                                         ),
                          'applylin')
    groundtruth.connect([(inputnode, applylin, [('epi', 'input_image'),
                                                 ('anat_head', 'reference_image')]),
                        (nonreg, applylin, [('outputnode.lin_anat2epi', 'transforms')])])
    
    
    # apply nonlinear warp
    applynonlin = Node(ants.ApplyTransforms(dimension=3,
                                            output_image='nonlin_coreg.nii.gz',
                                            invert_transform_flags=[True,False]
                                               ),
                          'applynonlin')
    groundtruth.connect([(inputnode, applynonlin, [('epi', 'input_image'),
                                                       ('anat_head', 'reference_image')]),
                        (transformlist, applynonlin, [('transformlist', 'transforms')])])
    
    # reduce ants field
    def reduce_ants_field(in_file,out_file):
        import nibabel as nb
        import os
        full_file = nb.load(in_file)
        data = full_file.get_data()
        reduced_file=nb.Nifti1Image(data[:,:,:,0,1], full_file.get_affine())
        nb.save(reduced_file, out_file)
        return os.path.abspath(out_file)
        
    reduce_ants = Node(util.Function(input_names=['in_file', 'out_file'],
                                    output_names=['out_file'],
                                    function=reduce_ants_field),
                      name='reduce_field')
    
    reduce_ants.inputs.out_file='nonlin_field.nii.gz'
    groundtruth.connect([(nonreg, reduce_ants, [('outputnode.nonlin_epi2anat', 'in_file')])])
    
    # mask ants field
    mask= Node(fsl.ImageMaths(op_string='-mul',
                              out_file='nonlin_field_masked.nii.gz'), 
               name='mask_fields')
    
    groundtruth.connect([(inputnode, mask, [('fmap_mask', 'in_file2')]),
                        (reduce_ants, mask, [('out_file', 'in_file')])])


    # calculate correlation between linear and nonlinear coreg
    correlation = Node(util.Function(input_names=['image1', 'image2', 'mask'],
                                 output_names=['linreg_stats'],
                                 function=calc_img_spearmanr),
                   name='correlation')

    def write_text(stats, filename):
        import numpy as np
        import os
        stats_array= np.array(stats)
        np.savetxt(filename, stats_array, delimiter=' ', fmt='%f')
        return os.path.abspath(filename)
    
    correlation_txt = Node(util.Function(input_names=['stats', 'filename'],
                                          output_names=['txtfile'],
                                          function=write_text),
                         name='correlation_txt')
    correlation_txt.inputs.filename='correlation_lin_nonlin.txt'
    groundtruth.connect([(applylin, correlation, [('output_image', 'image1')]),
                         (applynonlin, correlation, [('output_image', 'image2')]),
                         (inputnode, correlation, [('anat_brain_mask', 'mask')]),
                         (correlation, correlation_txt, [('linreg_stats', 'stats')])])


    # calcluate similarity of lin nonlin coreg to anatomy
    lin_sim = MapNode(interface = nutil.Similarity(),
                      name = 'similarity_lin',
                      iterfield=['metric'])
    lin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
    nonlin_sim = lin_sim.clone(name='similarity_nonlin')
    nonlin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

    def write_simtext(lin_metrics, nonlin_metrics, filename):
        import numpy as np
        import os
        lin_array = np.array(lin_metrics)
        lin_array=lin_array.reshape(np.size(lin_array),1)
        nonlin_array = np.array(nonlin_metrics)
        nonlin_array=nonlin_array.reshape(np.size(nonlin_array),1)
        metrics=np.concatenate((lin_array, nonlin_array),axis=1)
        metrics_file = filename
        np.savetxt(metrics_file, metrics, delimiter=' ', fmt='%f')
        return os.path.abspath(filename)
    
    write_sim_txt = Node(util.Function(input_names=['lin_metrics', 'nonlin_metrics', 'filename'],
                                      output_names=['txtfile'],
                                      function=write_simtext),
                  name='write_sim_txt')
    write_sim_txt.inputs.filename='similarity.txt'
    
    groundtruth.connect([(inputnode, lin_sim, [('anat_brain', 'volume1'),
                                               ('anat_brain_mask', 'mask1'),
                                               ('anat_brain_mask', 'mask2')]),
                       (applylin, lin_sim, [('output_image', 'volume2')]),
                       (inputnode, nonlin_sim, [('anat_brain', 'volume1'),
                                               ('anat_brain_mask', 'mask1'),
                                               ('anat_brain_mask', 'mask2')]),
                       (applynonlin, nonlin_sim, [('output_image', 'volume2')]),
                       (lin_sim, write_sim_txt, [('similarity', 'lin_metrics')]),
                       (nonlin_sim, write_sim_txt, [('similarity', 'nonlin_metrics')])
                       ])


    #connections to outputnode
    groundtruth.connect([(applylin, outputnode, [('output_image', 'lin_coreg')]),
                (applynonlin, outputnode, [('output_image', 'nonlin_coreg')]),
                (reduce_ants, outputnode, [('out_file', 'nonlin_field')]),
                (mask, outputnode, [('out_file', 'nonlin_field_masked')]),
                (correlation_txt, outputnode, [('txtfile', 'corr_txtfile')]),
                (write_sim_txt, outputnode, [('txtfile', 'sim_txtfile')])])


    
    return groundtruth
    
