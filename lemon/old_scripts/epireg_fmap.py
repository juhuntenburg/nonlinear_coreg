from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import os

epireg = Workflow(name='epireg')
epireg.base_dir='/scr/ilz1/nonlinear_registration/lemon/working_dir_epireg/'
data_dir = '/scr/ilz1/nonlinear_registration/lemon/results/'
output_dir = '/scr/ilz1/nonlinear_registration/lemon/results/'
echo_space=0.00067 #in sec
te_diff=2.46 #in ms
pe_dir='y-'
flirt_pe_dir=-2
subjects=['LEMON001']
#subjects=os.listdir(data_dir)

# infosource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# datasource to grab data
datasource = Node(nio.DataGrabber(infields=['subject_id'], 
                              outfields=['anat_head','anat_brain','epi_mean', 'fmap', 'mag_brain', 'mag_head'],
                              base_directory = os.path.abspath(data_dir),
                              template = '%s/%s/%s/%s',
                              template_args=dict(anat_head=[['subject_id','realignment', 'subject_id', '?']], 
                                                 anat_brain=[['subject_id','realignment', 'subject_id', '?']],
                                                 epi_mean=[['subject_id','realignment', 'subject_id', 'cmrrmbep2drestings007a001_mcf_mean.nii.gz']],
                                                 fmap=[['subject_id','fieldmap', 'subject_id', 'grefieldmappings004a2001_fslprepared.nii.gz']],
                                                 mag_brain=[['subject_id','fieldmap', 'subject_id', 'grefieldmappings003a1001_1_brain.nii.gz']], #using the non-eroded? as it is only used for registration, not for masking the fmap here
                                                 mag_head=[['subject_id','fieldmap', 'subject_id', 'grefieldmappings003a1001_1.nii.gz']]),
                              sort_filelist = True),
                  name='datasource')
epireg.connect(infosource, 'subject_id', datasource, 'subject_id')

# running fast segmentation
segment = Node(fsl.FAST(),
               name='segment')
epireg.connect(datasource, 'anat_brain', segment, 'in_files')

# function to get second entry from list
def second_element(file_list):
    return file_list[1]

# white matter mask
wmseg = Node(fsl.maths.MathsCommand(args='-thr 0.5 -bin'),
                 name='wmseg')
epireg.connect(segment, ('partial_volume_files',second_element), wmseg, 'in_file')

# standard flirt registration epi to anat
epi2anat1 = Node(fsl.FLIRT(dof=6),
           name='epi2anat1')
epireg.connect(datasource,'anat_brain',epi2anat1, 'reference')
epireg.connect(datasource, 'epi_mean', epi2anat1, 'in_file')

# register prepared fieldmap to anatomy (first brain then apply to head)
fmap2anat1 = Node(fsl.FLIRT(dof=6),
                 name='fmap2anat1')

fmap2anat2 = Node(fsl.FLIRT(dof=6, 
                            no_search=True),
                  name='fmap2anat2')
epireg.connect([(datasource,fmap2anat1,[('mag_brain', 'in_file'),
                                        ('anat_brain', 'reference')]),
                (datasource, fmap2anat2, [('mag_head','in_file'),
                                          ('anat_head','reference')]),
                (fmap2anat1,fmap2anat2,[('out_matrix_file','in_matrix_file')])
                ])

# unmask prepared fieldmap
fmap_mask = Node(fsl.maths.MathsCommand(args='-abs -bin'),
                 name='fmap_mask')

fmap_unmask = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                       save_unmasked_fmap=True,
                       fmap_out_file='fmap_unmasked.nii.gz'),
             name='fmap_unmask')

epireg.connect([(datasource,fmap_mask,[('fmap', 'in_file')]),
                (datasource, fmap_unmask,[('fmap','fmap_in_file')]),
                (fmap_mask, fmap_unmask,[('out_file','mask_file')])
                ])

# fix extrapolation if fieldmap is too small
innermask1 = Node(fsl.ApplyWarp(),
                  name='innermask1')

innermask2 = Node(fsl.maths.MathsCommand(args='-abs -bin'),
                 name='innermask2')

fmap_dilate = Node(fsl.FUGUE(unwarp_direction=pe_dir,
                       save_unmasked_fmap=True,
                       fmap_out_file='fmap_unmasked_dilated.nii.gz'),
             name='fmap_dilate')

epireg.connect([(fmap_unmask, innermask1,[('fmap_out_file','in_file')]),
              (datasource,innermask1,[('anat_head','ref_file')]),
              (fmap2anat2,innermask1,[('out_matrix_file','premat')]),
              (innermask1,innermask2,[('out_file','in_file')]),
              (innermask1,fmap_dilate,[('out_file','fmap_in_file')]),
              (innermask2,fmap_dilate,[('out_file','mask_file')]),
              ])

# running bbr with fieldmap
epi2anat2 = Node(fsl.FLIRT(dof=6,
                           cost='bbr',
                           echospacing=echo_space,
                           pedir=flirt_pe_dir,
                           schedule=os.path.abspath('/usr/share/fsl/5.0/etc/flirtsch/bbr.sch')),
           name='epi2anat2')

epireg.connect([(datasource,epi2anat2,[('anat_head','reference'),
                                       ('epi_mean','in_file')]),
                (epi2anat1,epi2anat2,[('out_matrix_file','in_matrix_file')]),
                (fmap_dilate, epi2anat2,[('fmap_out_file','fieldmap')]),
                (wmseg, epi2anat2,[('out_file','wm_seg')])
                ])
                
# get prepared fieldmap into epi space (fmap2anat plus epi2anat_inv)
# invert epi2anat -> anat2epi
inv_epi2anat = Node(fsl.ConvertXFM(invert_xfm=True),
                    name='inv_anat2epi')

concat_fmapreg = Node(fsl.ConvertXFM(concat_xfm=True),
                      name='concat_fmapreg')

fmap2epi = Node(fsl.ApplyWarp(),
                name='fmap2epi')

epireg.connect([(epi2anat2, inv_epi2anat, [('out_matrix_file','in_file')]),
                (fmap2anat2, concat_fmapreg, [('out_matrix_file', 'in_file')]),
                (inv_epi2anat, concat_fmapreg, [('out_file','in_file2')]),
                (concat_fmapreg,fmap2epi,[('out_file','premat')]),
                (fmap_unmask, fmap2epi,[('fmap_out_file','in_file')]),
                (datasource, fmap2epi,[('epi_mean','ref_file')])
                ])

# create shiftmap from fieldmap
fmap_mask2 = Node(fsl.maths.MathsCommand(args='-abs -bin'),
                 name='fmap_mask2')

shiftmap = Node(fsl.FUGUE(unwarp_direction='y-',
                          dwell_time=echo_space,
                          save_shift=True,
                          save_unmasked_shift=True,
                          shift_out_file='shiftmap_unmasked.nii.gz'),
             name='shiftmap')

epireg.connect([(fmap2epi, fmap_mask2,[('out_file', 'in_file')]),
                (fmap2epi, shiftmap, [('out_file','fmap_in_file')]),
                (fmap_mask2, shiftmap,[('out_file','mask_file')])
                ])

epireg.run()


#### run freesurfer bbregister to refine?

# convert all transformations to one warp
# $FSLDIR/bin/convertwarp -r ${vrefhead} -s ${vout}_fieldmaprads2epi_shift --postmat=${vout}.mat -o ${vout}_warp --shiftdir=${fdir} --relout
# to be applied in order
# (moco)
# shiftmap 'shift_out_file' (fmap shiftmap)
# epi2anat2 'out_matrix_file' (complete epi2anat reg, after bbr -flirt


# epireg.connect(epi2anat1, 'out_matrix_file', ---) #${vout}_init.mat
# epireg.connect(fmap2anat2, 'out_matrix_file', ---)#$-omat ${vout}_fieldmap2str.mat 
# epireg.connect(fmap2anat2, 'out_file', ---) # -out ${vout}_fieldmap2str 
# innermask1 'out_file' #${vout}_fieldmaprads2str_pad0
# innermask2 'out_file' #${vout}_fieldmaprads2str_innermask
# epi2anat2 'out_matrix_file' #${vout}.mat
# epi2anat2 'out_file ' #${vout}_1vol
# fmap_dilate 'fmap_out_file' #${vout}_fieldmaprads2str
# wmseg 'out_file' #${vout}_fast_wmseg
# inv_epi2anat 'out_file' #${vout}_inv.mat
# concat_fmapreg 'out_file' #${vout}_fieldmaprads2epi.mat
# fmap2epi 'out_file' #{vout}_fieldmaprads2epi
# fmap_unmask, 'fmap_out_file'# ${vout}_fieldmaprads_unmasked
# fmap_mask2, 'out_file' #${vout}_fieldmaprads2epi_mask
# shiftmap 'shift_out_file' #${vout}_fieldmaprads2epi_shift