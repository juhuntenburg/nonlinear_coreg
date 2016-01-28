from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.ants as ants
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
fmap = Workflow(name='fmap')

# inputnode 
inputnode=Node(util.IdentityInterface(fields=['epi_mean',
                                              'mag',
                                              'phase',
                                              'anat_head',
                                              'anat_brain']),
               name='inputnode')

# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['wmseg', 
                                               'fmap', 
                                               'fmap_shiftmap', 
                                               'fmap_epi2anat',
                                               'fmap_warpfield',
                                               'fmap_mean_coreg']),
                name='outputnode')



#### prepare fieldmap #############################################################################################################

# strip magnitude image tight and erode even further
tightbet = Node(fsl.BET(frac=0.6),
           name='tightbet')
fmap.connect(inputnode,'mag', tightbet,'in_file')

erode = Node(fsl.maths.ErodeImage(kernel_shape='sphere',
                                 kernel_size=3,
                                 args='-ero -ero'),
            name='erode')
#erode.iterables=('args', ['','-ero', '-ero -ero'] )
fmap.connect(tightbet,'out_file', erode, 'in_file')

# prepare field map
prep_fmap = Node(fsl.epi.PrepareFieldmap(delta_TE=te_diff),
                 name='prep_fmap')
fmap.connect([(erode, prep_fmap, [('out_file', 'in_magnitude')]),
              (inputnode, prep_fmap, [('phase', 'in_phase')]),
              (prep_fmap, outputnode, [('out_fieldmap','fmap')])
              ])



#### register and unmask fieldmap for use in fugue #################################################################################

# create normal magnitude skullstrip
largebet = Node(fsl.BET(mask=True),
           name='largebet')
fmap.connect(inputnode,'mag', largebet,'in_file')

# calculate fieldmap to anatomy (first to brain then apply to head)
fmap2anat1 = Node(fsl.FLIRT(dof=6),
                 name='fmap2anat1')

fmap2anat2 = Node(fsl.FLIRT(dof=6, 
                            no_search=True),
                  name='fmap2anat2')
fmap.connect([(largebet,fmap2anat1,[('out_file', 'in_file')]),
              (inputnode, fmap2anat1, [('anat_brain', 'reference')]),
              (inputnode, fmap2anat2, [('mag','in_file'),
                                       ('anat_head','reference')]),
              (fmap2anat1,fmap2anat2,[('out_matrix_file','in_matrix_file')])
              ])

# unmask fieldmap
unmask = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                       save_unmasked_fmap=True,
                       fmap_out_file='fmap_unmasked.nii.gz'),
             name='unmask')

fmap.connect([(prep_fmap, unmask,[('out_fieldmap','fmap_in_file')]),
              (largebet, unmask,[('mask_file','mask_file')])
              ])

# apply registration to actual fieldmap 
fmap2anat_apply = Node(fsl.ApplyWarp(),
                  name='fmap2anat_apply')

fmap.connect([(unmask, fmap2anat_apply,[('fmap_out_file','in_file')]),
              (inputnode,fmap2anat_apply,[('anat_head','ref_file')]),
              (fmap2anat2,fmap2anat_apply,[('out_matrix_file','premat')])
              ])

# fix extrapolation if fieldmap is too small
fmap2anat_innermask = Node(fsl.maths.MathsCommand(args='-abs -bin'),
                 name='fmap2anat_innermask')

fmap2anat_unmask2 = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                       save_unmasked_fmap=True,
                       fmap_out_file='fmap2anat_unmasked.nii.gz'),
             name='fmap2anat_unmask2')

fmap.connect([(fmap2anat_apply,fmap2anat_innermask,[('out_file','in_file')]),
              (fmap2anat_apply,fmap2anat_unmask2,[('out_file','fmap_in_file')]),
              (fmap2anat_innermask,fmap2anat_unmask2,[('out_file','mask_file')]),
              ])



#### fast segmentation for flirt bbr #############################################################################################

# running fast segmentation
segment = Node(fsl.FAST(),
               name='segment')
fmap.connect(inputnode, 'anat_brain', segment, 'in_files')

# function to get third entry from list
def third_element(file_list):
    return file_list[2]

# white matter mask
wmseg = Node(fsl.maths.MathsCommand(args='-thr 0.5 -bin',
                                    out_file='wmseg.nii.gz'),
                 name='wmseg')
fmap.connect(segment, ('partial_volume_files',third_element), wmseg, 'in_file')
fmap.connect([(wmseg,outputnode,[('out_file','wmseg')])])



#### register epi to anatomy with flirt bbr and fieldmap (and freesurfer?) ########################################################

# standard flirt registration epi to anat
epi2anat1 = Node(fsl.FLIRT(dof=6),
           name='epi2anat1')
fmap.connect([(inputnode,epi2anat1,[('anat_brain','reference'),
                                    ('epi_mean', 'in_file')])])

# running bbr with fieldmap
epi2anat2 = Node(fsl.FLIRT(dof=6,
                           cost='bbr',
                           echospacing=echo_space,
                           pedir=flirt_pe_dir,
                           schedule=os.path.abspath('/usr/share/fsl/5.0/etc/flirtsch/bbr.sch'),
                           out_matrix_file='fmap_epi2anat.mat'),
           name='epi2anat2')

fmap.connect([(inputnode,epi2anat2,[('anat_head','reference'),
                                    ('epi_mean','in_file')]),
              (epi2anat1,epi2anat2,[('out_matrix_file','in_matrix_file')]),
              (fmap2anat_unmask2, epi2anat2,[('fmap_out_file','fieldmap')]),
              (wmseg, epi2anat2,[('out_file','wm_seg')]),
              (epi2anat2, outputnode, [('out_matrix_file','fmap_epi2anat')])
              ])

# refine linear registration with bbregister
bbregister = Node(fs.BBRegister(contrast_tpye='t2',
                                out_fsl_file='fmap_fs_epi2anat',
                                subjects_dir=fs_subjects_dir),
                  name='bbregister')
  
fmap.connect([(epi2anat2, bbregister, [('out_matrix_file', 'init_reg_file')]),
               (inputnode, bbregister, [('epi_mean', 'source_file')]),
               (bbregister, outputnode, [('out_fsl_file', 'fmap_epi2anat')]) # undo for epi2anat2
               ])



#### create shiftmap to unwarp epi ################################################################################################

# transform fieldmap into epi space (fmap2anat plus epi2anat_inv)
inv_epi2anat = Node(fsl.ConvertXFM(invert_xfm=True),
                    name='inv_anat2epi')

concat_fmapreg = Node(fsl.ConvertXFM(concat_xfm=True),
                      name='concat_fmapreg')

fmap2epi = Node(fsl.ApplyWarp(),
                name='fmap2epi')

fmap.connect([(epi2anat2, inv_epi2anat, [('out_matrix_file','in_file')]),
              (fmap2anat2, concat_fmapreg, [('out_matrix_file', 'in_file')]),
              (inv_epi2anat, concat_fmapreg, [('out_file','in_file2')]),
              (concat_fmapreg,fmap2epi,[('out_file','premat')]),
              (unmask, fmap2epi,[('fmap_out_file','in_file')]),
              (inputnode, fmap2epi,[('epi_mean','ref_file')])
              ])

# create shiftmap from fieldmap
fmap2epi_mask = Node(fsl.maths.MathsCommand(args='-abs -bin'),
                     name='fmap2epi_mask')

shiftmap = Node(fsl.FUGUE(unwarp_direction='y-',
                          dwell_time=echo_space,
                          save_shift=True,
                          save_unmasked_shift=True,
                          shift_out_file='fmap_shiftmap.nii.gz'),
             name='shiftmap')

fmap.connect([(fmap2epi, fmap2epi_mask,[('out_file', 'in_file')]),
              (fmap2epi, shiftmap, [('out_file','fmap_in_file')]),
              (fmap2epi_mask, shiftmap,[('out_file','mask_file')]),
              (shiftmap, outputnode, [('shift_out_file', 'fmap_shiftmap')])
              ])
    

#### create complete warp from distorted epi to anatomical space #################################################################

fullwarp = Node(fsl.utils.ConvertWarp(relout=True,
                                      shiftdir=pe_dir,
                                      out_field='fmap_warpfield.nii.gz'),
                 name='fullwarp')

fmap.connect([(inputnode, fullwarp, [('anat_head', 'reference')]),
              (shiftmap, fullwarp, [('shift_out_file', 'shiftmap')]),
              (epi2anat2, fullwarp, [('out_matrix_file', 'postmat')]),
              (fullwarp, outputnode, [('out_field', 'fmap_warpfield')])
              ])
    
    
#### apply warpfield to mean epi #################################################################################################

warpmean = Node(fsl.preprocess.ApplyWarp(relwarp=True,
                                         interp='spline',
                                         out_file='fmap_mean_coreg.nii.gz'),
                name='warpmean')

fmap.connect([(inputnode, warpmean, [('epi_mean', 'in_file'),
                                     ('anat_head', 'ref_file')]),
              (fullwarp, warpmean, [('out_field', 'field_file')]),
              (warpmean, outputnode, [('out_file', 'fmap_mean_coreg')])])

 
#    return fmap


#### running directly ############################################################################################################

fmap.base_dir='/scr/jessica2/Schaare/LEMON/working_dir'
fmap.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir = '/scr/jessica2/Schaare/LEMON/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=['LEMON001']
# subjects=os.listdir(out_dir)
# subjects.remove('LEMON025')
# subjects.remove('LEMON013')
# subjects.remove('LEMON014')
# subjects.remove('LEMON064')
# subjects.remove('LEMON065')

# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# define templates and select files
templates={'epi_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'anat_head': 'preprocessed/{subject_id}/skullstrip/uni_reoriented.nii',
           'anat_brain': 'preprocessed/{subject_id}/skullstrip/uni_stripped.nii',
           'mag': 'raw/{subject_id}/rest/fmap_mag_1.nii.gz',
           'phase': 'raw/{subject_id}/rest/fmap_phase.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')

# connect to core workflow

fmap.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
              (infosource, sink, [('subject_id', 'container')]),
              (selectfiles, inputnode, [('epi_mean', 'epi_mean'),
                                        ('anat_head', 'anat_head'),
                                        ('anat_brain', 'anat_brain'),
                                        ('phase', 'phase'),
                                        ('mag', 'mag')]),
              (outputnode, sink, [('wmseg','fieldmap.@wmseg'),
                                  ('fmap','fieldmap.@fmap'),
                                  ('fmap_shiftmap','fieldmap.@shift'),
                                  ('fmap_epi2anat','fieldmap.@epi2anat'),
                                  ('fmap_warpfield', 'fieldmap.@warp'),
                                  ('fmap_mean_coreg', 'fieldmap.@mean')])
                      ])

                                               
fmap.run()
    