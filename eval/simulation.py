# see readme file for how to get the simulated data
#import libraries
from nipype.pipeline.engine import Node, Workflow
from nipype.interfaces import Function
from nipype.utils.filemanip import filename_to_list
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.ants as ants
import nipype.interfaces.c3 as c3
import nipype.interfaces.freesurfer as fs
from epi_t1_nonlinear import create_epi_t1_nonlinear_pipeline
import os


def create_simulation_workflow(name):
    
    pe_voxel_size=2.3 #has to be changed in the shiftmap scaling node directly!
    unwarp_direction='y-'
    
    # workflow
    simulation = Workflow(name=name)
    
    # inputnode
    inputnode=Node(util.IdentityInterface(fields=['dwell',
                                                  'anat_head',
                                                  'distorted_epi',
                                                  'fmap_mask',
                                                  'fmap_unmasked',
                                                  'shiftmap',
                                                  'freesurfer_dir',
                                                  'freesurfer_id',
                                                  'norm_lin',
                                                  'norm_invwarp',
                                                  'nonreg_mask'
                                                  ]),
                   name='inputnode')
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['lin_coreg', 
                                                   'nonlin_coreg',
                                                   'fmap_coreg',
                                                   'nonlin_field',
                                                   'nonlin_field_masked',
                                                   'fmap_field_masked',
                                                   ]),
                    name='outputnode')

        
    # epi to t1 nonlinear core workflow
    nonreg= create_epi_t1_nonlinear_pipeline('nonreg')
    simulation.connect([(inputnode, nonreg, [('distorted_epi', 'inputnode.realigned_epi'),
                                             ('freesurfer_dir','inputnode.fs_subjects_dir'),
                                             ('freesurfer_id', 'inputnode.fs_subject_id')])])
    
    simulation.connect([(inputnode, nonreg, [('norm_lin', 'inputnode.norm_lin'),
                                             ('norm_invwarp', 'inputnode.norm_invwarp'),
                                             ('nonreg_mask', 'inputnode.fmap_mask')])])
    
    #make list from transforms
    def makelist(string1, string2):
        transformlist=[string1, string2]
        return transformlist
       
    transformlist = Node(interface=Function(input_names=['string1', 'string2'],output_names=['transformlist'],
                                            function=makelist),name='transformlist')
      
    simulation.connect([(nonreg, transformlist, [('outputnode.nonlin_epi2anat', 'string2'),
                                                 ('outputnode.lin_anat2epi', 'string1')])])
                    
    # apply linear part of warp
    applylin = Node(ants.ApplyTransforms(dimension=3,
                                         output_image='lin_coreg.nii.gz',
                                         invert_transform_flags=[True]
                                         ),
                          'applylin')
    simulation.connect([(inputnode, applylin, [('distorted_epi', 'input_image'),
                                                 ('anat_head', 'reference_image')]),
                        (nonreg, applylin, [('outputnode.lin_anat2epi', 'transforms')]),
                        (applylin, outputnode, [('output_image', 'lin_coreg')])])
    
    
    # apply nonlinear warp
    applynonlin = Node(ants.ApplyTransforms(dimension=3,
                                               output_image='nonlin_coreg.nii.gz',
                                               invert_transform_flags=[True,False]
                                               ),
                          'applynonlin')
    simulation.connect([(inputnode, applynonlin, [('distorted_epi', 'input_image'),
                                                       ('anat_head', 'reference_image')]),
                        (transformlist, applynonlin, [('transformlist', 'transforms')]),
                        (applynonlin, outputnode, [('output_image', 'nonlin_coreg')])])
    
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
    simulation.connect([(nonreg, reduce_ants, [('outputnode.nonlin_epi2anat', 'in_file')]),
                        (reduce_ants, outputnode, [('out_file', 'nonlin_field')])])
    
    # mask ants field
    mask= Node(fsl.ImageMaths(op_string='-mul',
                              out_file='nonlin_field_masked.nii.gz'), 
               name='mask_fields')
    
    simulation.connect([(inputnode, mask, [('fmap_mask', 'in_file2')]),
                        (reduce_ants, mask, [('out_file', 'in_file')]),
                        (mask, outputnode, [('out_file', 'nonlin_field_masked')])])
    
    
    # mask and scale shiftmap
    shiftmap = Node(fsl.MultiImageMaths(op_string='-mul %s -mul 2.3',
                                     out_file='original_field_masked.nii.gz'),
                     name='shiftmap')
    simulation.connect([(inputnode, shiftmap, [('shiftmap', 'in_file'),
                                               (('fmap_mask',filename_to_list), 'operand_files')]),
                        (shiftmap, outputnode, [('out_file', 'fmap_field_masked')])
                        ])
    
    
    # re-unwarp using the fmap
    fmap = Node(fsl.FUGUE(unwarp_direction=unwarp_direction,
                          smooth3d=2.0,
                          save_shift=True,
                          unwarped_file='fmap_unwarped.nii.gz',
                          shift_out_file='fmap_field.nii.gz'),
                 name='fmap')
    
    # function to get dwelltime as float from dwell string variable
    def dwell2dwelltime(dwell):
        dwellstring='0.'+dwell
        dwelltime=float(dwellstring)
        return dwelltime
    
    simulation.connect([(inputnode, fmap, [(('dwell', dwell2dwelltime), 'dwell_time'),
                                           ('fmap_unmasked','fmap_in_file' ),
                                           ('distorted_epi', 'in_file'),
                                           ('fmap_mask', 'mask_file')])])
                        
    
    # register fieldmap corrected to anatomy with bbregister
    bbregister = Node(interface=fs.BBRegister(init='fsl', 
                                              contrast_type='t2', 
                                              out_fsl_file = True), 
                     name='bbregister')
    
    simulation.connect([(fmap, bbregister, [('unwarped_file', 'source_file')]),
                        (inputnode, bbregister, [('freesurfer_dir','subjects_dir'),
                                                 ('freesurfer_id', 'subject_id')])])
    
    # convert shiftmap and coreg matrix to one warpfield and apply 
    convertwarp =  Node(fsl.utils.ConvertWarp(shiftdir=unwarp_direction,
                                              relout=True,
                                              out_field='fmap_fullwarp.nii.gz'),
                         name='convertwarp')
       
    applywarp_fmap = Node(fsl.ApplyWarp(interp='trilinear',
                                   relwarp=True,
                                   out_file='fmap_coreg.nii.gz'),
                     name='applywarp_fmap') 
       
    simulation.connect([(inputnode, convertwarp, [('anat_head', 'reference')]),
                        (fmap, convertwarp, [('shift_out_file', 'shiftmap')]),
                        (bbregister, convertwarp, [('out_fsl_file', 'postmat')]),
                        (inputnode, applywarp_fmap, [('distorted_epi', 'in_file'),
                                                       ('anat_head', 'ref_file')]),
                        (convertwarp, applywarp_fmap, [('out_field', 'field_file')]),
                        (applywarp_fmap, outputnode, [('out_file', 'fmap_coreg')])])
    
    return simulation
    
