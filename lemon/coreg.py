from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.ants as ants
from nipype.utils.filemanip import filename_to_list
import nipype.interfaces.c3 as c3
import os

#### workflow, in and output node #################################################################################################

# initiate workflow
coreg = Workflow(name='coreg')


#inputnode 
inputnode=Node(util.IdentityInterface(fields=['epi_mean',
                                              'anat_head',
                                              'anat_brain',
                                              'subject_id',
                                              'fs_subjects_dir',
                                              #'wmseg'
                                              ]),
               name='inputnode')

# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['wmseg',
                                               'anat_head',
                                               'anat_brain',
                                               'epi2anat_dat',
                                               'epi2anat_mat',
                                               'epi2anat_itk',
                                               'lin_mean_coreg']),
                name='outputnode')



#### convert mgz files to niigz #################################################################################################

brain_convert=Node(fs.MRIConvert(out_type='niigz'),
                   name='brain_convert')

head_convert=Node(fs.MRIConvert(out_type='niigz'),
                   name='head_convert')

coreg.connect([(inputnode, brain_convert, [('anat_brain','in_file')]),
               (inputnode, head_convert, [('anat_head', 'in_file')]),
               (brain_convert, outputnode, [('out_file', 'anat_brain')]),
               (head_convert, outputnode, [('out_file', 'anat_head')])
               ])


#### fast segmentation for flirt bbr #############################################################################################

#running fast segmentation
segment = Node(fsl.FAST(),
               name='segment')
coreg.connect(brain_convert, 'out_file', segment, 'in_files')
   
# function to get third entry from list
def third_element(file_list):
    return file_list[2]
#   
# # white matter mask
wmseg = Node(fsl.maths.MathsCommand(args='-thr 0.5 -bin',
                                    out_file='brain_out_wmseg.nii.gz'),
                 name='wmseg')
coreg.connect(segment, ('partial_volume_files',third_element), wmseg, 'in_file')
coreg.connect([(wmseg,outputnode,[('out_file','wmseg')])])



#### register epi to anatomy #####################################################################################################

# standard flirt registration epi to anat
epi2anat1 = Node(fsl.FLIRT(dof=6),
            name='epi2anat1')

coreg.connect([(inputnode,epi2anat1,[('epi_mean', 'in_file')]),
               (brain_convert, epi2anat1, [('out_file','reference')])
               ])

# running flirt bbr
epi2anat2 = Node(fsl.FLIRT(dof=6,
                           cost='bbr',
                           schedule=os.path.abspath('/usr/share/fsl/5.0/etc/flirtsch/bbr.sch'),
                           out_matrix_file='fsl_epi2anat.mat',
                           out_file='fsl_mean_coreg.nii.gz'),
           name='epi2anat2')

coreg.connect([(inputnode,epi2anat2,[('epi_mean', 'in_file')]),
               (brain_convert, epi2anat2, [('out_file','reference')]),
               (epi2anat1, epi2anat2, [('out_matrix_file', 'in_matrix_file')]),
               (wmseg, epi2anat2,[('out_file','wm_seg')]),
               #(inputnode, epi2anat2, [('wmseg', 'wm_seg')])
              ])


# transform transform
tkregister2 = Node(fs.utils.Tkregister2(noedit=True,
                                        out_reg_file='fsl_epi2anat.dat'),
                   name='tkregister2')

coreg.connect([(epi2anat2,tkregister2, [('out_matrix_file', 'fsl')]),
               (inputnode, tkregister2, [('epi_mean', 'mov'),
                                         ('subject_id', 'subject_id'),
                                         ('fs_subjects_dir','subjects_dir')])
               ])


# refine linear registration with bbregister
bbregister = Node(fs.BBRegister(contrast_type='t2',
                                out_fsl_file='lin_epi2anat.mat',
                                out_reg_file='lin_epi2anat.dat',
                                ),
                name='bbregister')

coreg.connect([(tkregister2, bbregister, [('out_reg_file','init_reg_file')]),
               (inputnode, bbregister, [('epi_mean', 'source_file'),
                                        ('fs_subjects_dir', 'subjects_dir'),
                                        ('subject_id', 'subject_id')]),
               (bbregister, outputnode, [('out_fsl_file', 'epi2anat_mat'),
                                         ('out_reg_file', 'epi2anat_dat'),
                                         ]),
               ])


# convert transform to itk
itk = Node(interface=c3.C3dAffineTool(fsl2ras=True,
                                      itk_transform='lin_epi2anat_affine.txt'), 
                 name='itk')

coreg.connect([(inputnode, itk, [('epi_mean', 'source_file')]),
              (head_convert, itk, [('out_file', 'reference_file')]),
              (bbregister, itk, [('out_fsl_file', 'transform_file')]),
              (itk, outputnode, [('itk_transform', 'epi2anat_itk')])
               ])

# apply with ants
applytransform = Node(ants.ApplyTransforms(dimension=3,
                                                   output_image='lin_mean_coreg.nii.gz',
                                                   interpolation = 'BSpline'),
                      'applytransform')
 
coreg.connect([(inputnode, applytransform, [('epi_mean', 'input_image')]),
               (head_convert, applytransform, [('out_file', 'reference_image')]),
               (itk, applytransform, [(('itk_transform', filename_to_list), 'transforms')]),
               (applytransform, outputnode, [('output_image', 'lin_mean_coreg')])
                ])



#### setting up in and output, running  ############################################################################################################

coreg.base_dir='/scr/kansas1/huntenburg/lemon_missing/working_dir/'
#coreg.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir='/scr/jessica2/Schaare/LEMON/'
fs_subjects_dir='/scr/jessica2/Schaare/LEMON/freesurfer/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/missing_subjects.txt','r')
for line in f:
    subjects.append(line.strip())


# infosource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id','fs_subjects_dir']), 
                  name='infosource')
infosource.inputs.fs_subjects_dir=fs_subjects_dir
infosource.iterables=('subject_id', subjects)

# select files
templates={'epi_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'anat_head': 'freesurfer/{subject_id}/mri/T1.mgz',
           'anat_brain': 'freesurfer/{subject_id}/mri/brain.mgz',
           #'wmseg':'preprocessed/{subject_id}/freesurfer_anatomy/brain_out_wmseg.nii.gz'
           }

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

#sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')
 
# connect to core workflow 
coreg.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
               (infosource, inputnode, [('subject_id', 'subject_id'),
                                        ('fs_subjects_dir','fs_subjects_dir')]),
               (selectfiles, inputnode, [('epi_mean', 'epi_mean'),
                                        ('anat_head', 'anat_head'),
                                        ('anat_brain', 'anat_brain'),
                                        #('wmseg', 'wmseg')
                                        ]),
                (infosource, sink, [('subject_id', 'container')]),
                (outputnode, sink, [('epi2anat_dat','coreg.@epi2anat_dat'),
                                    ('epi2anat_mat', 'coreg.@epi2anat_mat'),
                                    ('epi2anat_itk', 'coreg.@epi2anat_itk'),
                                    ('anat_head', 'freesurfer_anatomy.@anat_head'),
                                    ('anat_brain', 'freesurfer_anatomy.@anat_brain'),
                                    ('wmseg','freesurfer_anatomy.@anat_brain_wmseg'),
                                    ('lin_mean_coreg', 'coreg.@lin_mean_coreg')
                                   ])    
                    ])

coreg.run(plugin='CondorDAGMan')
