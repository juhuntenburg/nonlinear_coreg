from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.c3 as c3
import nipype.interfaces.ants as ants
from nipype.interfaces import Function
from nipype.utils.filemanip import filename_to_list
import os

##### set basic parameters ########################################################################################################
echo_space=0.00067 #in sec
te_diff=2.46 #in ms
pe_dir='-y'
shift_dir='y-'

# fsl output type
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')


#### workflow, in and output node #################################################################################################
# initiate workflow
fmap = Workflow(name='fmap')

#inputnode 
inputnode=Node(util.IdentityInterface(fields=['mag',
                                              'phase',
                                              'epi_mean',
                                              'anat_head',
                                              'anat_brain',
                                              'fs_subjects_dir',
                                              'subject_id'
                                              ]),
               name='inputnode')

# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['fmap', 
                                               'shiftmap',
                                               'warpfield',
                                               #'fullwarp',
                                               #'fs_fullwarp',
                                               #'epireg',
                                               #'fmap_flirt_mean_coreg',
                                               #'fmap2str_mat',
                                               #'fmap2epi_mat',
                                               #'fmap_epi',
                                               #'fmap_str',
                                               #'epi2anat_mat',
                                               'wmedge',
                                               'fmap_epi2anat_mat',
                                               #'fmap_epi2anat_dat',
                                               #'fmap_epi2anat_itk',
                                               #'fmap_fs_mean_coreg',
                                               'fmap_mean_coreg'
                                               ]),            
                name='outputnode')



#### prepare fieldmap #############################################################################################################

# strip magnitude image and erode even further
bet = Node(fsl.BET(frac=0.6,
                        mask=True),
           name='bet')
fmap.connect(inputnode,'mag', bet,'in_file')
#            reo_mag, 'out_file', bet, 'in_file')

erode = Node(fsl.maths.ErodeImage(kernel_shape='sphere',
                                 kernel_size=3,
                                 args=''),
            name='erode')
fmap.connect(bet,'out_file', erode, 'in_file')

# prepare fieldmap
prep_fmap = Node(fsl.epi.PrepareFieldmap(delta_TE=te_diff),
                 name='prep_fmap')
fmap.connect([(erode, prep_fmap, [('out_file', 'in_magnitude')]),
              #(reo_phase, prep_fmap, [('out_file', 'in_phase')]),
              (inputnode, prep_fmap, [('phase', 'in_phase')]),
              (prep_fmap, outputnode, [('out_fieldmap','fmap')])
              ])



# reorient all  epi_reg input to standard

# reo_mag=Node(fsl.Reorient2Std(),
#              name='reo_mag')
#   
# reo_epi=Node(fsl.Reorient2Std(),
#              name='reo_epi')
#   
# reo_anat_head=Node(fsl.Reorient2Std(),
#              name='reo_anat_head')
#   
# reo_anat_brain=Node(fsl.Reorient2Std(),
#              name='reo_anat_brain')
#   
# reo_phase=Node(fsl.Reorient2Std(),
#              name='reo_phase')
#  
# reo_fmap=Node(fsl.Reorient2Std(),
#               name='reo_fmap')
#   
# fmap.connect([(inputnode, reo_mag, [('mag', 'in_file')]),
#               (inputnode, reo_epi, [('epi_mean', 'in_file')]),
#               (inputnode, reo_anat_head, [('anat_head', 'in_file')]),
#               (inputnode, reo_anat_brain, [('anat_brain', 'in_file')]),
#               (prep_fmap, reo_fmap, [('out_fieldmap', 'in_file')])
#               ])


#### epi_reg skript ##################################################################################################################

# strip magnitude image less aggressive
magbet = Node(fsl.BET(frac=0.5,
                        mask=True),
           name='magbet')
#fmap.connect(reo_mag,'out_file', magbet,'in_file')
fmap.connect(inputnode,'mag', magbet,'in_file')


# run epi_reg skript
epireg=Node(fsl.epi.EpiReg(echospacing=echo_space,
                           pedir=pe_dir,
                           out_base='epireg'),
             name='epireg')

fmap.connect([#(reo_epi, epireg, [('out_file', 'epi')]),
              #(reo_anat_head, epireg, [('out_file', 't1_head')]),
              #(reo_anat_brain, epireg, [('out_file', 't1_brain')]),
              #(reo_mag, epireg, [('out_file', 'fmapmag')]),
              (inputnode, epireg, [('epi_mean', 'epi'),
                                   ('anat_head', 't1_head'),
                                   ('anat_brain', 't1_brain'),
                                   ('mag', 'fmapmag')]),
              (prep_fmap, epireg, [('out_fieldmap', 'fmap')]),
              #(reo_fmap, epireg, [('out_file', 'fmap')]),
              (magbet, epireg, [('out_file', 'fmapmagbrain')]),
              (epireg, outputnode, [#('out_file', 'epireg'),
#                                   ('out_flirt_file', 'fmap_flirt_mean_coreg'),
#                                   ('fmap2str_mat', 'fmap2str_mat'),
#                                   ('fmap2epi_mat', 'fmap2epi_mat'),
#                                   ('fmap_epi', 'fmap_epi'),
#                                   ('fmap_str', 'fmap_str'),
#                                   ('epi2str_mat', 'epi2anat_mat'),
#                                   ('fullwarp', 'fullwarp'),
                                    ('wmedge', 'wmedge'),
                                    ('shiftmap', 'shiftmap')])
              ])

#### refine with freesurfer bbregister #############################################################################################
bbregister = Node(fs.BBRegister(contrast_type='t2',
                                out_fsl_file='fmap_epi2anat.mat',
                                out_reg_file='fmap_epi2anat.dat',
                                registered_file='fmap_fs_out.nii.gz',
                                init='header'
                                ),
                name='bbregister')
  
fmap.connect([(epireg, bbregister, [('out_file', 'source_file')]),
              (inputnode, bbregister, [('fs_subjects_dir', 'subjects_dir'),
                                       ('subject_id', 'subject_id')])
               ])
  
  
# concatenate affine transformations from flirt and bbregister
concat=Node(fsl.ConvertXFM(concat_xfm = True,
                           out_file = 'fmap_epi2anat.mat' ),
            name='concat')
  
fmap.connect([(epireg, concat, [('epi2str_mat', 'in_file')]),
              (bbregister, concat, [('out_fsl_file', 'in_file2')]),
              (concat, outputnode, [('out_file', 'fmap_epi2anat_mat')])
              ])
               
  
# convert transform to itk
# itk = Node(interface=c3.C3dAffineTool(fsl2ras=True,
#                                       itk_transform='transform0GenericAffine.mat'), 
#                  name='itk')
#  
# fmap.connect([(inputnode, itk, [('epi_mean', 'source_file'),
#                                 ('anat_head', 'reference_file')]),
#               (concat, itk, [('out_file', 'transform_file')]),
#               (itk, outputnode, [('itk_transform', 'fmap_epi2anat_itk')])
#                ])

# # convert shiftmap to warpfield
# convertwarp =  Node(fsl.utils.ConvertWarp(shiftdir=shift_dir,
#                                           relout=True,
#                                           out_field='transform1Warp.nii.gz'),
#                      name='convertwarp')
#  
# fmap.connect([(inputnode, convertwarp, [('anat_head', 'reference')]),
#               (epireg, convertwarp, [('shiftmap', 'shiftmap')]),
#               (convertwarp, outputnode, [('out_field', 'warpfield')])
#               ])
# 
# # make transformation list
# def makelist(string1, string2):
#     transformlist=[string1, string2]
#     return transformlist
#    
# transformlist = Node(interface=Function(input_names=['string1', 'string2'],
#                                         output_names=['transformlist'],
#                                         function=makelist),
#                      name='transformlist')
#   
# fmap.connect([(convertwarp, transformlist, [('out_field', 'string1')]),
#               (itk, transformlist, [('itk_transform', 'string2')])
#               ])
# 
# # apply with ants
# applytransform = Node(ants.WarpImageMultiTransform(dimension=3,
#                                                    output_image='fmap_mean_coreg.nii.gz'),
#                       'applytransform')
#  
# fmap.connect([(inputnode, applytransform, [('epi_mean', 'input_image'),
#                                            ('anat_head', 'reference_image')]),
#               (transformlist, applytransform, [('transformlist', 'transformation_series')]),
#               (applytransform, outputnode, [('output_image', 'fmap_mean_coreg')])
#               ])


#### make new fullwarp and apply ####################################################################################################
convertwarp =  Node(fsl.utils.ConvertWarp(shiftdir=shift_dir,
                                          relout=True,
                                          out_field='fmap_coreg_warp.nii.gz'),
                     name='convertwarp')
      
applywarp = Node(fsl.ApplyWarp(interp='spline',
                               relwarp=True,
                               out_file='fmap_mean_coreg.nii.gz', 
                               datatype='float'),
                 name='applywarp') 
      
fmap.connect([(inputnode, convertwarp, [('anat_head', 'reference')]),
              (epireg, convertwarp, [('shiftmap', 'shiftmap')]),
              (concat, convertwarp, [('out_file', 'postmat')]),
              (inputnode, applywarp, [('epi_mean', 'in_file'),
                                      ('anat_head', 'ref_file')]),
             # (epibet, applywarp, [('out_file', 'in_file')]),
              (convertwarp, applywarp, [('out_field', 'field_file')]),
              (applywarp, outputnode, [('out_file', 'fmap_mean_coreg')]),
              (convertwarp, outputnode, [('out_field', 'warpfield')])
              ])


#### set in and outputs, run ########################################################################################################

fmap.base_dir='/scr/kansas1/huntenburg/'
#fmap.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir = '/scr/jessica2/Schaare/LEMON/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
fs_subjects_dir='/scr/jessica2/Schaare/LEMON/freesurfer/freesurfer/'
subjects=['LEMON039']
# subjects=[]
# f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
# for line in f:
#     subjects.append(line.strip())
# subjects.remove('LEMON027S')

# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id','fs_subjects_dir']), 
                  name='infosource')
infosource.inputs.fs_subjects_dir=fs_subjects_dir
infosource.iterables=('subject_id', subjects)

# define templates and select files
templates={'mag': 'raw/{subject_id}/rest/fmap_mag_1.nii.gz',
           'phase': 'raw/{subject_id}/rest/fmap_phase.nii.gz',
           'epi_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
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

fmap.connect([(infosource, inputnode, [('subject_id', 'subject_id'),
                                       ('fs_subjects_dir','fs_subjects_dir')]),
              (infosource, selectfiles, [('subject_id', 'subject_id')]),
              (infosource, sink, [('subject_id', 'container')]),
              (selectfiles, inputnode, [('phase', 'phase'),
                                        ('mag', 'mag'),
                                        ('epi_mean', 'epi_mean'),
                                        ('anat_head', 'anat_head'),
                                        ('anat_brain', 'anat_brain')
                                        ]),
            (outputnode, sink, [('fmap','fieldmap_coreg.@fmap'),
                                ('shiftmap','fieldmap_coreg.@shiftmap'),
                                ('warpfield','fieldmap_coreg.@warpfield'),
                                #(#'fs_fullwarp', 'fieldmap_coreg.@fs_fullwarp'),
                                #(#'epi2anat_mat','fieldmap_coreg.@epi2anat_mat'),
                                #(#'epireg','fieldmap_coreg.@epireg'),
                                ('fmap_epi2anat_mat', 'fieldmap_coreg.@fmap_epi2anat_mat' ),
                                ('fmap_mean_coreg','fieldmap_coreg.@fmap_mean_coreg'),
                                ('wmedge', 'freesurfer_anatomy.@brain_out_wmedge')
                                ])
              ])


fmap.run()#(plugin='CondorDAGMan')
    