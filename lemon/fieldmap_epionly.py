from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.c3 as c3
import nipype.interfaces.ants as ants
from nipype.utils.filemanip import filename_to_list
import os

#def create_fmap_pipeline(name='fmap'):

##### set basic parameters ########################################################################################################
echo_space=0.00067 #in sec
te_diff=2.46 #in ms
pe_dir='y-'
flirt_pe_dir=-2 
#fs_subjects_dir = ''

# fsl output type
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')


#### workflow, in and output node #################################################################################################
# initiate workflow
fmapepi = Workflow(name='fmap_coreg')

#inputnode 
inputnode=Node(util.IdentityInterface(fields=['epi_mean',
                                              'mag',
                                              'phase',
                                              'anat_head',
                                              'anat_brain',
                                              'subject_id',
                                              'fs_subjects_dir',
                                              'wmseg'
                                              ]),
               name='inputnode')

# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['fmap', 
                                               'fmap_shiftmap',
                                               #'fmap2epi',
                                               #'fmap2epi_mat',
                                               #'wmseg', 
                                               'epi2anat_mat',
                                               'epi2anat_dat',
                                               'epi2anat_itk',
                                               #'warpfield',
                                               'fmap_mean_coreg',
                                               'fmap_unwarped_mean']),
                name='outputnode')



#### prepare fieldmap #############################################################################################################

# strip magnitude image and erode even further
bet = Node(fsl.BET(frac=0.5,
                        mask=True),
           name='bet')
fmapepi.connect(inputnode,'mag', bet,'in_file')

erode = Node(fsl.maths.ErodeImage(kernel_shape='sphere',
                                 kernel_size=3,
                                 args=''),
            name='erode')
fmapepi.connect(bet,'out_file', erode, 'in_file')

# prepare fieldmap
prep_fmap = Node(fsl.epi.PrepareFieldmap(delta_TE=te_diff),
                 name='prep_fmap')
fmapepi.connect([(erode, prep_fmap, [('out_file', 'in_magnitude')]),
                 (inputnode, prep_fmap, [('phase', 'in_phase')]),
                 (prep_fmap, outputnode, [('out_fieldmap','fmap')])
                 ])


#### unmask fieldmap ##########################################################################################

fmap_mask = Node(fsl.maths.MathsCommand(args='-abs -bin'),
                 name='fmap_mask')

unmask = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                       save_unmasked_fmap=True,
                       fmap_out_file='fmap_unmasked.nii.gz'),
             name='unmask')

fmapepi.connect([(prep_fmap, fmap_mask, [('out_fieldmap', 'in_file')]),
                 (fmap_mask, unmask, [('out_file', 'mask_file')]),
                 (prep_fmap, unmask,[('out_fieldmap','fmap_in_file')])
                 ])


#### register fieldmap to epi #################################################################################

# calculate fieldmap to epi
# fmap2epi1 = Node(fsl.FLIRT(dof=6),
#                  name='fmap2epi1')
# 
# fmap2epi2 = Node(fsl.FLIRT(dof=6,
#                            no_search=True,
#                            out_matrix_file='fmap2epi.mat'),
#                   name='fmap2epi2')
# 
# fmapepi.connect([(bet,fmap2epi1,[('out_file', 'in_file')]),
#                  (inputnode, fmap2epi1, [('epi_mean', 'reference')]),
#                  (inputnode, fmap2epi2, [('mag','in_file'),
#                                          ('epi_mean','reference')]),
#                  (fmap2epi1,fmap2epi2,[('out_matrix_file','in_matrix_file')]),
#                  (fmap2epi2, outputnode, [('out_matrix_file', 'fmap2epi_mat')])
#                  ])
# 
# 
# # apply registration to fieldmap 
# fmap2epi_apply = Node(fsl.ApplyXfm(out_file='fmap2epi.nii.gz',
#                                    apply_xfm=True,
#                                    no_search=True),
#                   name='fmap2epi_apply')
# 
# fmapepi.connect([(unmask, fmap2epi_apply,[('fmap_out_file','in_file')]),
#                  (inputnode,fmap2epi_apply,[('epi_mean','reference')]),
#                  (fmap2epi2,fmap2epi_apply,[('out_matrix_file','in_matrix_file')]),
#                  (fmap2epi_apply, outputnode, [('out_file', 'fmap2epi')])
#                  ])


#### unwarp epi with fieldmap ####################################################################################################

# fmap2epi_mask = Node(fsl.maths.MathsCommand(args='-abs -bin'),
#                      name='fmap2epi_mask')

unwarp = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                          dwell_time=echo_space,
                          save_shift=True,
                          save_unmasked_shift=True,
                          unwarped_file='fmap_unwarped_mean.nii.gz',
                          shift_out_file='fmap_shiftmap.nii.gz'),
             name='unwarp')

fmapepi.connect([#(fmap2epi_apply, fmap2epi_mask,[('out_file', 'in_file')]),
                 (inputnode, unwarp, [('epi_mean', 'in_file')]),
                 #(fmap2epi_apply, unwarp, [('out_file','fmap_in_file')]),
                 (unmask, unwarp, [('fmap_out_file', 'fmap_in_file')]),
                 (fmap_mask, unwarp, [('out_file','mask_file')]),
                 #(fmap2epi_mask, unwarp,[('out_file','mask_file')]),
                 (unwarp, outputnode, [('shift_out_file', 'fmap_shiftmap')]),
                 (unwarp, outputnode, [('unwarped_file', 'fmap_unwarped_mean')])
                 ])




#### register epi to anatomy #####################################################################################################

# standard flirt registration epi to anat
epi2anat1 = Node(fsl.FLIRT(dof=6),
            name='epi2anat1')

fmapepi.connect([(unwarp,epi2anat1,[('unwarped_file', 'in_file')]),
               (inputnode, epi2anat1, [('anat_brain','reference')])
               ])

# running flirt bbr
epi2anat2 = Node(fsl.FLIRT(dof=6,
                           cost='bbr',
                           schedule=os.path.abspath('/usr/share/fsl/5.0/etc/flirtsch/bbr.sch'),
                           out_matrix_file='fsl_epi2anat.mat',
                           out_file='fsl_mean_coreg.nii.gz'),
           name='epi2anat2')

fmapepi.connect([(unwarp,epi2anat2,[('unwarped_file', 'in_file')]),
               (inputnode, epi2anat2, [('anat_brain','reference')]),
               (epi2anat1, epi2anat2, [('out_matrix_file', 'in_matrix_file')]),
               #(wmseg, epi2anat2,[('out_file','wm_seg')]),
               (inputnode, epi2anat2, [('wmseg', 'wm_seg')])
              ])


# transform transform
tkregister2 = Node(fs.utils.Tkregister2(noedit=True,
                                        out_reg_file='fsl_epi2anat.dat'),
                   name='tkregister2')

fmapepi.connect([(epi2anat2,tkregister2, [('out_matrix_file', 'fsl')]),
               (unwarp, tkregister2, [('unwarped_file', 'mov')]),
               (inputnode, tkregister2, [('subject_id', 'subject_id'),
                                         ('fs_subjects_dir','subjects_dir')])
               ])


# refine linear registration with bbregister
bbregister = Node(fs.BBRegister(contrast_type='t2',
                                out_fsl_file='fmap_epi2anat.mat',
                                out_reg_file='fmap_epi2anat.dat',
                                ),
                name='bbregister')

fmapepi.connect([(tkregister2, bbregister, [('out_reg_file','init_reg_file')]),
                 (unwarp, bbregister, [('unwarped_file', 'source_file')]),
               (inputnode, bbregister, [('fs_subjects_dir', 'subjects_dir'),
                                        ('subject_id', 'subject_id')]),
               (bbregister, outputnode, [('out_fsl_file', 'epi2anat_mat'),
                                         ('out_reg_file', 'epi2anat_dat'),
                                         ]),
               ])


# convert transform to itk
itk = Node(interface=c3.C3dAffineTool(fsl2ras=True,
                                      itk_transform='fmap_epi2anat_affine.txt'), 
                 name='itk')

fmapepi.connect([(inputnode, itk, [('anat_head', 'reference_file')]),
               (unwarp, itk, [('unwarped_file', 'source_file')]),
               (bbregister, itk, [('out_fsl_file', 'transform_file')]),
               (itk, outputnode, [('itk_transform', 'epi2anat_itk')])
               ])

# apply with ants
applytransform = Node(ants.ApplyTransforms(dimension=3,
                                                   output_image='fmap_mean_coreg.nii.gz',
                                                   interpolation = 'BSpline'),
                      'applytransform')
 
fmapepi.connect([(inputnode, applytransform, [('anat_head', 'reference_image')]),
               (unwarp, applytransform, [('unwarped_file', 'input_image')]),
               (itk, applytransform, [(('itk_transform', filename_to_list), 'transforms')]),
               (applytransform, outputnode, [('output_image', 'fmap_mean_coreg')])
                ])



#### running directly ############################################################################################################

fmapepi.base_dir='/scr/kansas1/huntenburg'
#fmapepi.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir = '/scr/jessica2/Schaare/LEMON/'
fs_subjects_dir='/scr/jessica2/Schaare/LEMON/freesurfer/freesurfer/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=['LEMON001']
# subjects=[]
# f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
# for line in f:
#     subjects.append(line.strip())
# subjects.remove('LEMON027')



# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id','fs_subjects_dir']), 
                  name='infosource')
infosource.inputs.fs_subjects_dir=fs_subjects_dir
infosource.iterables=('subject_id', subjects)

# define templates and select files
templates={'epi_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'mag': 'raw/{subject_id}/rest/fmap_mag_1.nii.gz',
           'phase': 'raw/{subject_id}/rest/fmap_phase.nii.gz',
           'anat_head': 'preprocessed/{subject_id}/freesurfer_anatomy/T1_out.nii.gz',
           'anat_brain': 'preprocessed/{subject_id}/freesurfer_anatomy/brain_out.nii.gz',
           'wmseg':'preprocessed/{subject_id}/freesurfer_anatomy/brain_out_wmseg.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')

# connect to core workflow

fmapepi.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
                 (infosource, inputnode, [('subject_id', 'subject_id'),
                                          ('fs_subjects_dir', 'fs_subjects_dir')]),
              (infosource, sink, [('subject_id', 'container')]),
              (selectfiles, inputnode, [('epi_mean', 'epi_mean'),
                                        ('phase', 'phase'),
                                        ('mag', 'mag'),
                                        ('anat_head','anat_head'),
                                        ('anat_brain', 'anat_brain'),
                                        ('wmseg', 'wmseg')]),
            (outputnode, sink, [('fmap','fieldmap_coreg.@fmap'),
                                ('fmap_shiftmap','fieldmap_coreg.@shift'),
                                ('fmap_unwarped_mean','fieldmap_coreg.@unwarped_mean'),
                                ('fmap_mean_coreg', 'fieldmap_coreg.@fmap_mean_coreg'),
                                ('epi2anat_mat', 'fieldmap_coreg.@epi2anat_mat'),
                                ('epi2anat_dat', 'fieldmap_coreg.@epi2anat_dat'),
                                ('epi2anat_itk', 'fieldmap_coreg.@epi2anat_itk')])
                ])
                                               
fmapepi.run()#(plugin='CondorDAGMan')
    