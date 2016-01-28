##### this has changed from last full run in terms of the mask for fieldmap unmasking
##### i.e. the topupbet step has been included
##### its more appropriate (and it works) yet doesnt really make a difference in the final resulat
##### it requires topup to run again in order for getting the corrected files

from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.freesurfer as fs
import os

    
# fsl output type
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

echo_space=0.00067 #in sec
datain = '/scr/jessica2/Schaare/LEMON/topup_datain.txt'
pe_dir='y'
shift_dir='y'


# initiate workflow
topup=Workflow(name='topup_epi2topup_masked')

# inputnode
inputnode=Node(util.IdentityInterface(fields=['epi_mean',
                                              'se1',
                                              'se_inv1',
                                              'se2',
                                              'se_inv2',
                                              'anat_head',
                                              'anat_brain',
                                              'subject_id',
                                              'fs_subjects_dir',
                                              #'topup_field',
                                              'wmseg']),
               name='inputnode')

# outputnode                                 
outputnode=Node(util.IdentityInterface(fields=['topup_fmap',
                                               'topup_corrected',
                                               'unwarpfield2se',
                                               'epi2anat_mat',
                                               'epi2anat_dat',
                                               'topup_fullwarp',
                                               'topup_mean_coreg',
                                               'topup_field'
                                               ]),
                name='outputnode')


# create ordered list of se images
merge_list=Node(util.Merge(4),
                name='merge_list')
 
topup.connect([(inputnode, merge_list, [('se1','in1'),
                                        ('se_inv1','in2'),
                                        ('se2','in3'),
                                        ('se_inv2','in4')])])
          
# merge all se images into one 4D file
merge=Node(fsl.Merge(dimension='t'),
           name='merge')
topup.connect([(merge_list,merge,[('out','in_files')])])
 
# calculate topup_field
topup_field=Node(fsl.TOPUP(out_base='topup',
                           encoding_file = datain),
                name='topup_field')
topup.connect([(merge,topup_field,[('merged_file','in_file')]),
               (topup_field, outputnode,[('out_field', 'topup_field')])
               ])

# multiply topup field 2 pi to get rads/sec
topup_fmap=Node(fsl.maths.BinaryMaths(operation='mul',
                                      operand_value=6.28318530718,
                                      out_file = 'topup_fmap.nii.gz'),
                 name='topup_fmap')
topup.connect([#(inputnode, topup_fmap, [('topup_field', 'in_file')]),
               (topup_field,topup_fmap,[('out_field','in_file')]),
               (topup_fmap, outputnode, [('out_file', 'topup_fmap')])
               ])

# extract one of the corrected files to be used as mask
split=Node(fsl.Split(dimension='t',
                       out_base_name='topup_corrected'),
             name='split')

def first_element(file_list):
    return file_list[0]

topupbet = Node(fsl.BET(frac=0.3),
           name='topupet')

topup.connect([(topup_field, split, [('out_corrected', 'in_file')]),
               (split, topupbet, [(('out_files', first_element),'in_file')])
               ])


#### unmask fieldmap ############################################################################################################

fmap_mask = Node(fsl.maths.MathsCommand(args='-abs -bin'),
                 name='fmap_mask')

unmask = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                       save_unmasked_fmap=True,
                       fmap_out_file='fmap_unmasked.nii.gz'),
             name='unmask')

topup.connect([(topupbet, fmap_mask, [('out_file', 'in_file')]),
               #(topup_fmap, fmap_mask, [('out_file', 'in_file')]),
               (fmap_mask, unmask, [('out_file', 'mask_file')]),
               (topup_fmap, unmask,[('out_file','fmap_in_file')])
                 ])

### register epi to fieldmap ###################################################################################################
 
epi2se = Node(fsl.FLIRT(dof=6),
                name='epi2se')

topup.connect([(inputnode,epi2se,[('epi_mean', 'in_file'),
                                  ('se1', 'reference')])
               ])

#### unwarp epi with fieldmap ####################################################################################################)

unwarp = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                          dwell_time=echo_space,
                          save_shift=True,
                          save_unmasked_shift=True,
                          unwarped_file='topup_unwarped_mean.nii.gz',
                          shift_out_file='topup_shiftmap.nii.gz'),
             name='unwarp')

topup.connect([(epi2se, unwarp, [('out_file', 'in_file')]),
               (unmask, unwarp, [('fmap_out_file', 'fmap_in_file')]),
               (fmap_mask, unwarp, [('out_file','mask_file')])
               ])

#### make warpfield and apply
# make warpfield and apply
convertwarp0 =  Node(fsl.utils.ConvertWarp(shiftdir=shift_dir,
                                          relout=True,
                                          out_field='unwarpfield_epi2se.nii.gz'),
                     name='convertwarp0')
   
applywarp0 = Node(fsl.ApplyWarp(interp='spline',
                               relwarp=True,
                               out_file='unwarped_epi2se.nii.gz', 
                               datatype='float'),
                 name='applywarp0') 
   
topup.connect([(inputnode, convertwarp0, [('se1', 'reference')]),
                 (epi2se, convertwarp0, [('out_matrix_file', 'premat')]),
                 (unwarp, convertwarp0, [('shift_out_file', 'shiftmap')]),
                 (inputnode, applywarp0, [('epi_mean', 'in_file'),
                                         ('se1', 'ref_file')]),
                 (convertwarp0, applywarp0, [('out_field', 'field_file')]),
                 (convertwarp0, outputnode, [('out_field', 'unwarpfield2se')])
              ])

#### register epi to anatomy #####################################################################################################

# standard flirt registration epi to anat
epi2anat1 = Node(fsl.FLIRT(dof=6),
            name='epi2anat1')

topup.connect([(applywarp0,epi2anat1,[('out_file', 'in_file')]),
               (inputnode, epi2anat1, [('anat_brain','reference')])
               ])

# running flirt bbr
epi2anat2 = Node(fsl.FLIRT(dof=6,
                           cost='bbr',
                           schedule=os.path.abspath('/usr/share/fsl/5.0/etc/flirtsch/bbr.sch'),
                           out_matrix_file='fsl_epi2anat.mat',
                           out_file='fsl_mean_coreg.nii.gz'),
           name='epi2anat2')

topup.connect([(applywarp0,epi2anat2,[('out_file', 'in_file')]),
               (inputnode, epi2anat2, [('anat_brain','reference')]),
               (epi2anat1, epi2anat2, [('out_matrix_file', 'in_matrix_file')]),
               #(wmseg, epi2anat2,[('out_file','wm_seg')]),
               (inputnode, epi2anat2, [('wmseg', 'wm_seg')])
              ])


# transform transform
tkregister2 = Node(fs.utils.Tkregister2(noedit=True,
                                        out_reg_file='fsl_epi2anat.dat'),
                   name='tkregister2')

topup.connect([(epi2anat2,tkregister2, [('out_matrix_file', 'fsl')]),
               (applywarp0, tkregister2, [('out_file', 'mov')]),
               (inputnode, tkregister2, [('subject_id', 'subject_id'),
                                         ('fs_subjects_dir','subjects_dir')])
               ])


# refine linear registration with bbregister
bbregister = Node(fs.BBRegister(contrast_type='t2',
                                out_fsl_file='topup_epi2anat.mat',
                                out_reg_file='topup_epi2anat.dat',
                                ),
                name='bbregister')

topup.connect([(tkregister2, bbregister, [('out_reg_file','init_reg_file')]),
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
                                          out_field='topup_fullwarp.nii.gz'),
                     name='convertwarp')
   
applywarp = Node(fsl.ApplyWarp(interp='spline',
                               relwarp=True,
                               out_file='topup_mean_coreg.nii.gz', 
                               datatype='float'),
                 name='applywarp') 
   
topup.connect([(inputnode, convertwarp, [('anat_head', 'reference')]),
                 (convertwarp0, convertwarp, [('out_field', 'warp1')]),
                 (bbregister, convertwarp, [('out_fsl_file', 'postmat')]),
                 (inputnode, applywarp, [('epi_mean', 'in_file'),
                                         ('anat_head', 'ref_file')]),
                 (convertwarp, applywarp, [('out_field', 'field_file')]),
                 (applywarp, outputnode, [('out_file', 'topup_mean_coreg')]),
                 (convertwarp, outputnode, [('out_field', 'topup_fullwarp')])
              ])


##### in and output ############

topup.base_dir='/scr/kansas1/huntenburg/lemon_missing/working_dir/'
#topup.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir='/scr/jessica2/Schaare/LEMON/'
fs_subjects_dir='/scr/jessica2/Schaare/LEMON/freesurfer/freesurfer/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/missing_subjects.txt','r')
for line in f:
    subjects.append(line.strip())


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id','fs_subjects_dir']), 
                  name='infosource')
infosource.inputs.fs_subjects_dir=fs_subjects_dir
infosource.iterables=('subject_id', subjects)

# select files
templates={'epi_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'se1': 'raw/{subject_id}/rest/se_1.nii.gz',
           'se_inv1': 'raw/{subject_id}/rest/se_inv1.nii.gz',
           'se2': 'raw/{subject_id}/rest/se_2.nii.gz',
           'se_inv2': 'raw/{subject_id}/rest/se_inv2.nii.gz',
           'anat_head': 'preprocessed/{subject_id}/freesurfer_anatomy/T1_out.nii.gz',
           'anat_brain': 'preprocessed/{subject_id}/freesurfer_anatomy/brain_out.nii.gz',
           'wmseg':'preprocessed/{subject_id}/freesurfer_anatomy/brain_out_wmseg.nii.gz',
           #'topup_field': 'kansas1/huntenburg/topup_applytopup/_subject_id_{subject_id}/topup_field/topup_field.nii.gz'
           }

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

#sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')
 
# connect to core workflow 
topup.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
               (infosource, inputnode, [('subject_id', 'subject_id'),
                                        ('fs_subjects_dir', 'fs_subjects_dir')]),
               (selectfiles, inputnode, [('epi_mean', 'epi_mean'),
                                         ('se1', 'se1'),
                                         ('se_inv1','se_inv1'),
                                         ('se2', 'se2'),
                                         ('se_inv2', 'se_inv2'),
                                         ('anat_head','anat_head'),
                                         ('anat_brain', 'anat_brain'),
                                         #('topup_field','topup_field'),
                                         ('wmseg','wmseg')
                                         ]),
               #(inputnode, outputnode, [('topup_field', 'topup_field')]),
               (infosource, sink, [('subject_id', 'container')]),
                (outputnode, sink, [('topup_fmap','topup_coreg.@fmap'),
                                    ('topup_fullwarp','topup_coreg.@fullwarp'),
                                    ('epi2anat_mat','topup_coreg.@epi2anat_mat'),
                                    ('epi2anat_dat','topup_coreg.@epi2anat_dat'),
                                    ('unwarpfield2se','topup_coreg.@unwarpfield2se'),
                                    ('topup_mean_coreg','topup_coreg.@topup_mean_coreg'),
                                    ('topup_field', 'topup_coreg.@topup_field')
                                    ])                
               ])

topup.run(plugin='CondorDAGMan')


