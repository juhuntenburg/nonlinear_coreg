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
topup=Workflow(name='topup')

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
                                              'mag']),
               name='inputnode')

# outputnode                                 
outputnode=Node(util.IdentityInterface(fields=['topup_field',
                                               'topup_fmap',
                                               'topup_corrected',
                                               'surr_magbrain',
                                               'epireg',
                                               'epi2anat_mat',
                                               'shiftmap',
                                               'topup_fullwarp',
                                               'topup_mean_coreg'
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
               (topup_field, outputnode,[('out_field', 'topup_field'),
                                         ('out_corrected', 'topup_corrected')])
               ])

# multiply topup field 2 pi to get rads/sec
topup_fmap=Node(fsl.maths.BinaryMaths(operation='mul',
                                      operand_value=6.28318530718,
                                      out_file = 'topup_fmap.nii.gz'),
                 name='topup_fmap')
topup.connect([(topup_field,topup_fmap,[('out_field','in_file')]),
               (topup_fmap, outputnode, [('out_file', 'topup_fmap')])
               ])

# extract one of the corrected files to be used as mag_brain to epi_reg
split=Node(fsl.Split(dimension='t',
                       out_base_name='topup_corrected'),
             name='split')

def first_element(file_list):
    return file_list[0]

magbet = Node(fsl.BET(frac=0.3),
           name='magbet')

topup.connect([(topup_field, split, [('out_corrected', 'in_file')]),
               (split, magbet, [(('out_files', first_element),'in_file')]),
               (magbet, outputnode, [('out_file', 'surr_magbrain')])
               ])

# register wholehead magnitude image to surr_magbrain to use in epireg
magflirt = Node(fsl.FLIRT(dof=6),
             name='flirt')

topup.connect([(inputnode, magflirt, [('mag', 'in_file')]),
               (split, magflirt, [(('out_files', first_element), 'reference')])
               ])


# run epireg with topup fieldmap as input
epireg=Node(fsl.epi.EpiReg(echospacing=echo_space,
                           pedir=pe_dir,
                           out_base='epireg'),
             name='epireg')

topup.connect([(inputnode, epireg, [('epi_mean', 'epi'),
                                   ('anat_head', 't1_head'),
                                   ('anat_brain', 't1_brain')]),
                (topup_fmap, epireg, [('out_file', 'fmap')]),
                (magbet, epireg, [('out_file', 'fmapmagbrain')]),
                (magflirt, epireg, [('out_file', 'fmapmag')]),
                (epireg, outputnode, [('out_file', 'epireg'),
                                      ('shiftmap', 'shiftmap')])
              ])


#### refine with freesurfer bbregister #############################################################################################
bbregister = Node(fs.BBRegister(contrast_type='t2',
                                out_fsl_file='topup_fs_epi2anat.mat',
                                out_reg_file='topup_fs_epi2anat.dat',
                                registered_file='topup_fs_out.nii.gz',
                                init='header'
                                ),
                name='bbregister')

topup.connect([(epireg, bbregister, [('out_file', 'source_file')]),
               (inputnode, bbregister, [('fs_subjects_dir', 'subjects_dir'),
                                        ('subject_id', 'subject_id')])
               ])


# concatenate affine transformations from flirt and bbregister
concat=Node(fsl.ConvertXFM(concat_xfm = True,
                           out_file = 'topup_epi2anat.mat' ),
            name='concat')

topup.connect([(epireg, concat, [('epi2str_mat', 'in_file')]),
              (bbregister, concat, [('out_fsl_file', 'in_file2')]),
              (concat, outputnode, [('out_file', 'epi2anat_mat')])
              ])
             

#### make new fullwarp and apply ####################################################################################################
convertwarp =  Node(fsl.utils.ConvertWarp(shiftdir=shift_dir,
                                          relout=True,
                                          out_field='topup_coreg_fullwarp.nii.gz'),
                     name='convertwarp')
   
applywarp = Node(fsl.ApplyWarp(interp='spline',
                               relwarp=True,
                               out_file='topup_mean_coreg.nii.gz', 
                               datatype='float'),
                 name='applywarp') 
   
topup.connect([(inputnode, convertwarp, [('anat_head', 'reference')]),
              (epireg, convertwarp, [('shiftmap', 'shiftmap')]),
              (concat, convertwarp, [('out_file', 'postmat')]),
              (inputnode, applywarp, [('epi_mean', 'in_file'),
                                      ('anat_head', 'ref_file')]),
              (convertwarp, applywarp, [('out_field', 'field_file')]),
              (applywarp, outputnode, [('out_file', 'topup_mean_coreg')]),
              (convertwarp, outputnode, [('out_field', 'topup_fullwarp')])
              ])



##### in and output ############

topup.base_dir='/scr/kansas1/huntenburg/'
topup.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir='/scr/jessica2/Schaare/LEMON/'
fs_subjects_dir='/scr/jessica2/Schaare/LEMON/freesurfer/freesurfer/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=['LEMON001']
# subjects=[]
# f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
# for line in f:
#     subjects.append(line.strip())


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id','fs_subjects_dir']), 
                  name='infosource')
infosource.inputs.fs_subjects_dir=fs_subjects_dir
infosource.iterables=('subject_id', subjects)

# select files
templates={'epi_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'mag':'raw/{subject_id}/rest/fmap_mag_1.nii.gz',
           'se1': 'raw/{subject_id}/rest/se_1.nii.gz',
           'se_inv1': 'raw/{subject_id}/rest/se_inv1.nii.gz',
           'se2': 'raw/{subject_id}/rest/se_2.nii.gz',
           'se_inv2': 'raw/{subject_id}/rest/se_inv2.nii.gz',
           'anat_head': 'preprocessed/{subject_id}/freesurfer_anatomy/T1_out.nii.gz',
           'anat_brain': 'preprocessed/{subject_id}/freesurfer_anatomy/brain_out.nii.gz',
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
                                         ('mag', 'mag')]),
               (infosource, sink, [('subject_id', 'container')]),
               (outputnode, sink, [('topup_fmap','topup_coreg.@fmap'),
                                   ('shiftmap','topup_coreg.@shiftmap'),
                                   ('topup_fullwarp','topup_coreg.@fullwarp'),
                                   ('epi2anat_mat','topup_coreg.@epi2anat_mat'),
                                   #('epireg','topup_coreg.@epireg'),
                                   ('topup_mean_coreg','topup_coreg.@topup_mean_coreg')
                                   ])                
               
               ])

topup.run()


