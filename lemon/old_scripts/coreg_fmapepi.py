from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.freesurfer as fs
import os

#### workflow, in and output node #################################################################################################

shift_dir='y-'


# initiate workflow
coreg = Workflow(name='coreg_fmapepi')


#inputnode 
inputnode=Node(util.IdentityInterface(fields=['epi_mean',
                                              'epi_unwarped',
                                              'anat_head',
                                              'anat_brain',
                                              'shiftmap2epi',
                                              'subject_id',
                                              'fs_subjects_dir',
                                              'wmseg']),
               name='inputnode')

# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['anat_head',
                                               'anat_brain',
                                               'fsl_epi2anat_mat',
                                               'fs_epi2anat_mat',
                                               'fs_epi2anat_mat_fsl_style',
                                               'fsl_mean_coreg',
                                               'fs_mean_coreg',
                                               'fs_fullwarp']),
                name='outputnode')


#### register epi to anatomy #####################################################################################################

#standard flirt registration epi to anat
epi2anat1 = Node(fsl.FLIRT(dof=6),
            name='epi2anat1')

coreg.connect([(inputnode,epi2anat1,[('epi_unwarped', 'in_file'),
                                     ('anat_brain', 'reference')])
               ])

# running flirt bbr
epi2anat2 = Node(fsl.FLIRT(dof=6,
                           cost='bbr',
                           schedule=os.path.abspath('/usr/share/fsl/5.0/etc/flirtsch/bbr.sch'),
                           out_matrix_file='fsl_epi2anat.mat',
                           out_file='fsl_mean_coreg.nii.gz'),
           name='epi2anat2')

coreg.connect([(inputnode,epi2anat2,[('epi_unwarped', 'in_file'),
                                     ('wmseg', 'wm_seg'),
                                     ('anat_brain', 'reference')]),
               (epi2anat1, epi2anat2, [('out_matrix_file', 'in_matrix_file')]),
               #(wmseg, epi2anat2,[('out_file','wm_seg')]),
               (epi2anat2, outputnode, [('out_matrix_file','fsl_epi2anat_mat'),
                                        ('out_file', 'fsl_mean_coreg')])
              ])


# transform transform
tkregister2 = Node(fs.utils.Tkregister2(noedit=True,
                                        out_reg_file='fsl_epi2anat.dat'),
                   name='tkregister2')

coreg.connect([(epi2anat2,tkregister2, [('out_matrix_file', 'fsl')]),
               (inputnode, tkregister2, [('epi_unwarped', 'mov'),
                                         ('subject_id', 'subject_id'),
                                         ('fs_subjects_dir','subjects_dir')])
               ])


# refine linear registration with bbregister
bbregister = Node(fs.BBRegister(contrast_type='t2',
                                out_fsl_file='fs_epi2anat.mat',
                                out_reg_file='fs_epi2anat.dat',
                                registered_file='fs_mean_coreg.nii.gz'
                                ),
                name='bbregister')

coreg.connect([(tkregister2, bbregister, [('out_reg_file','init_reg_file')]),
               (inputnode, bbregister, [('epi_unwarped', 'source_file'),
                                        ('fs_subjects_dir', 'subjects_dir'),
                                        ('subject_id', 'subject_id')]),
               (bbregister, outputnode, [('out_fsl_file', 'fs_epi2anat_mat_fsl_style'),
                                         ('out_reg_file', 'fs_epi2anat_mat'),
                                         #('registered_file','fs_mean_coreg')
                                         ]),
               ])
  
  
#### make new fullwarp and apply ####################################################################################################
convertwarp =  Node(fsl.utils.ConvertWarp(shiftdir=shift_dir,
                                          relout=True,
                                          out_field='fmap_fullwarp.nii.gz'),
                     name='convertwarp')
   
applywarp = Node(fsl.ApplyWarp(interp='spline',
                               relwarp=True,
                               out_file='fmap_mean_coreg.nii.gz', 
                               datatype='float'),
                 name='applywarp') 
   
coreg.connect([(inputnode, convertwarp, [('anat_head', 'reference'),
                                         ('shiftmap2epi', 'shiftmap')]),
                (bbregister, convertwarp, [('out_fsl_file', 'postmat')]),
                (inputnode, applywarp, [('epi_mean', 'in_file'),
                                        ('anat_head', 'ref_file')]),
             # (epibet, applywarp, [('out_file', 'in_file')]),
              (convertwarp, applywarp, [('out_field', 'field_file')]),
              (applywarp, outputnode, [('out_file', 'fs_mean_coreg')]),
              (convertwarp, outputnode, [('out_field', 'fs_fullwarp')])
              ])

#### setting up in and output, running  ############################################################################################################

coreg.base_dir='/scr/jessica2/Schaare/LEMON/working_dir/'
coreg.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir='/scr/jessica2/Schaare/LEMON/'
fs_subjects_dir='/scr/jessica2/Schaare/LEMON/freesurfer/freesurfer/'
#out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=['LEMON003']
# subjects=os.listdir(fs_subjects_dir)
# subjects.remove('LEMON013')
# subjects.remove('LEMON064')


# infosource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id','fs_subjects_dir']), 
                  name='infosource')
infosource.inputs.fs_subjects_dir=fs_subjects_dir
infosource.iterables=('subject_id', subjects)

# select files
templates={'epi_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'epi_unwarped':'working_dir/fmapepi/_subject_id_{subject_id}/unwarp/fmap_unwarped_mean.nii.gz',
           'shiftmap2epi':'working_dir/fmapepi/_subject_id_{subject_id}/unwarp/fmap_shiftmap2epi.nii.gz',
           'wmseg': 'preprocessed/{subject_id}/freesurfer_anatomy/brain_out_wmseg.nii.gz',
           'anat_head': 'preprocessed/{subject_id}/freesurfer_anatomy/T1_out.nii.gz',
           'anat_brain': 'preprocessed/{subject_id}/freesurfer_anatomy/brain_out.nii.gz'
           }

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# sink to store files
# sink = Node(nio.DataSink(base_directory=out_dir,
#                           parameterization=False), 
#              name='sink')
 
# connect to core workflow 
coreg.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
               (infosource, inputnode, [('subject_id', 'subject_id'),
                                        ('fs_subjects_dir','fs_subjects_dir')]),
               (selectfiles, inputnode, [('epi_mean', 'epi_mean'),
                                        ('anat_head', 'anat_head'),
                                        ('anat_brain', 'anat_brain'),
                                        ('wmseg', 'wmseg'),
                                        ('epi_unwarped','epi_unwarped'),
                                        ('shiftmap2epi', 'shiftmap2epi')]),
#                (infosource, sink, [('subject_id', 'container')]),
#                (outputnode, sink, [('wmseg','coreg.@wmseg'),
#                                    ('fs_epi2anat_mat','coreg.@fs_epi2anat_mat'),
#                                    ('fs_epi2anat_mat_fsl_style', 'coreg.@fs_epi2anat_mat_fsl_style'),
#                                    ('fs_mean_coreg','coreg.@fs_mean_coreg'),
#                                    ('fsl_epi2anat_mat','coreg.@fsl_epi2anat_mat'),
#                                    ('fsl_mean_coreg','coreg.@fsl_mean_coreg'),
#                                    ('anat_head', 'freesurfer_anatomy.@anat_head'),
#                                    ('anat_brain', 'freesurfer_anatomy.@anat_brain')
#                                   ])    
                    ])

coreg.run() #(plugin='CondorDAGMan')





