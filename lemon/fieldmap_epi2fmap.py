from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.freesurfer as fs
import os

#def create_fmap_pipeline(name='fmap'):

##### set basic parameters ########################################################################################################
echo_space=0.00067 #in sec
te_diff=2.46 #in ms
pe_dir='y-'
flirt_pe_dir=-2 
shift_dir='y-'

# fsl output type
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')


#### workflow, in and output node #################################################################################################
# initiate workflow
fmapepi = Workflow(name='fmap_epi2fmap')

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
                                               'unwarpfield2fmap',
                                               'epi2anat_mat',
                                               'epi2anat_dat',
                                               'fmap_mean_coreg',
                                               'fmap_fullwarp']),
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

### register epi to fieldmap ###################################################################################################
 
epi2fmap = Node(fsl.FLIRT(dof=6),
                name='epi2fmap')

fmapepi.connect([(inputnode,epi2fmap,[('epi_mean', 'in_file'),
                                      ('mag', 'reference')])
               ])

#### unwarp epi with fieldmap ####################################################################################################)

unwarp = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                          dwell_time=echo_space,
                          save_shift=True,
                          save_unmasked_shift=True,
                          unwarped_file='fmap_unwarped_mean.nii.gz',
                          shift_out_file='fmap_shiftmap.nii.gz'),
             name='unwarp')

fmapepi.connect([(epi2fmap, unwarp, [('out_file', 'in_file')]),
                 (unmask, unwarp, [('fmap_out_file', 'fmap_in_file')]),
                 (fmap_mask, unwarp, [('out_file','mask_file')])
                 ])

#### make warpfield and apply
# make warpfield and apply
convertwarp0 =  Node(fsl.utils.ConvertWarp(shiftdir=shift_dir,
                                           #shift_direction=shift_dir,
                                          #out_relwarp=True,
                                          relout=True,
                                          out_field='unwarpfield_epi2fmap.nii.gz'),
                                          #out_file='unwarpfield_epi2fmap.nii.gz'),
                     name='convertwarp0')
   
applywarp0 = Node(fsl.ApplyWarp(interp='spline',
                               relwarp=True,
                               out_file='unwarped_epi2fmap.nii.gz', 
                               datatype='float'),
                 name='applywarp0') 
    
fmapepi.connect([(inputnode, convertwarp0, [('mag', 'reference')]),
                 (epi2fmap, convertwarp0, [('out_matrix_file', 'premat')]),
                 (unwarp, convertwarp0, [('shift_out_file', 'shiftmap')]),
                 #(unwarp, convertwarp0, [('shift_out_file', 'shift_in_file')]),
                 (inputnode, applywarp0, [('epi_mean', 'in_file'),
                                         ('mag', 'ref_file')]),
                 #(convertwarp0, applywarp0, [('out_file', 'field_file')]),
                 #(convertwarp0, outputnode, [('out_file', 'unwarpfield2fmap')])
                 (convertwarp0, applywarp0, [('out_field', 'field_file')]),
                 (convertwarp0, outputnode, [('out_field', 'unwarpfield2fmap')])
              ])

#### register epi to anatomy #####################################################################################################

#standard flirt registration epi to anat
epi2anat1 = Node(fsl.FLIRT(dof=6),
            name='epi2anat1')
 
fmapepi.connect([(applywarp0,epi2anat1,[('out_file', 'in_file')]),
               (inputnode, epi2anat1, [('anat_brain','reference')])
               ])
 
# running flirt bbr
epi2anat2 = Node(fsl.FLIRT(dof=6,
                           cost='bbr',
                           schedule=os.path.abspath('/usr/share/fsl/5.0/etc/flirtsch/bbr.sch'),
                           out_matrix_file='fsl_epi2anat.mat',
                           out_file='fsl_mean_coreg.nii.gz'),
           name='epi2anat2')
 
fmapepi.connect([(applywarp0,epi2anat2,[('out_file', 'in_file')]),
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
               (applywarp0, tkregister2, [('out_file', 'mov')]),
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
                 (applywarp0, bbregister, [('out_file', 'source_file')]),
               (inputnode, bbregister, [('fs_subjects_dir', 'subjects_dir'),
                                        ('subject_id', 'subject_id')]),
               (bbregister, outputnode, [('out_fsl_file', 'epi2anat_mat'),
                                         ('out_reg_file', 'epi2anat_dat'),
                                         ]),
               ])
 
 
# make warpfield and apply
convertwarp =  Node(fsl.utils.ConvertWarp(shiftdir=shift_dir,
                                          relout=True,
                                          out_field='fmap_fullwarp.nii.gz'),
                     name='convertwarp')
    
applywarp = Node(fsl.ApplyWarp(interp='spline',
                               relwarp=True,
                               out_file='fmap_mean_coreg.nii.gz', 
                               datatype='float'),
                 name='applywarp') 
    
fmapepi.connect([(inputnode, convertwarp, [('anat_head', 'reference')]),
                 (convertwarp0, convertwarp, [('out_field', 'warp1')]),
                 (bbregister, convertwarp, [('out_fsl_file', 'postmat')]),
                 (inputnode, applywarp, [('epi_mean', 'in_file'),
                                         ('anat_head', 'ref_file')]),
                 (convertwarp, applywarp, [('out_field', 'field_file')]),
                 (applywarp, outputnode, [('out_file', 'fmap_mean_coreg')]),
                 (convertwarp, outputnode, [('out_field', 'fmap_fullwarp')])
              ])



#### running directly ############################################################################################################

fmapepi.base_dir='/scr/kansas1/huntenburg/lemon_missing/working_dir/'
#fmapepi.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir = '/scr/jessica2/Schaare/LEMON/'
fs_subjects_dir='/scr/jessica2/Schaare/LEMON/freesurfer/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
#subjects=['LEMON001']
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/missing_subjects.txt','r')
for line in f:
    subjects.append(line.strip())

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

#sink to store files
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
                                ('fmap_mean_coreg', 'fieldmap_coreg.@fmap_mean_coreg'),
                                ('unwarpfield2fmap', 'fieldmap_coreg.@unwarpfield2fmap'),
                                ('fmap_fullwarp', 'fieldmap_coreg.@fmap_fullwarp'),
                                ('epi2anat_mat', 'fieldmap_coreg.@epi2anat_mat'),
                                ('epi2anat_dat', 'fieldmap_coreg.@epi2anat_dat')
                                ])
                ])
                                               
fmapepi.run(plugin='CondorDAGMan')
    