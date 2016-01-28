from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import os

fmap = Workflow(name='fmap')
fmap.base_dir='/scr/ilz1/nonlinear_registration/lemon/working_dir/'
data_dir = '/scr/kalifornien1/data/lemon/lemon_id/'
output_dir = '/scr/ilz1/nonlinear_registration/lemon/results/'
echo_space=0.00067 #in sec
te_diff=2.46 #in ms

#subjects = ['LEMON001']
subjects=os.listdir(data_dir)

# infosource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# datasource to grab data
datasource = Node(nio.DataGrabber(infields=['subject_id'], 
                              outfields=['mag','phase','rest'],
                              base_directory = os.path.abspath(data_dir),
                              template = '%s/%s',
                              template_args=dict(mag=[['subject_id','grefieldmappings003a1001_1.nii.gz']], 
                                                 phase=[['subject_id','grefieldmappings004a2001.nii.gz']],
                                                 rest=[['subject_id','cmrrmbep2drestings007a001.nii.gz']]),
                              sort_filelist = True),
                  name='datasource')
fmap.connect(infosource, 'subject_id', datasource, 'subject_id')

# sink to store data
sink = Node(nio.DataSink(base_directory=output_dir,
                          substitutions=[('_subject_id_', ''),
                                         ('_args_', 'ero')]), 
             name='sink')
fmap.connect(infosource, 'subject_id', sink, 'container')

# rest timeseries motion correction
mcflirt = Node(fsl.MCFLIRT(output_type = 'NIFTI_GZ',
                           save_mats=True,
                           save_plots=True), 
               name='mcflirt')
fmap.connect([(datasource, mcflirt, [('rest', 'in_file')]),
              (mcflirt, sink, [('par_file','realignment'),
                               ('mat_file','realignment.@matrices')])
              ])

# tmean
tmean = Node(fsl.maths.MeanImage(dimension='T',
                                 output_type = 'NIFTI_GZ'), 
                 name='tmean')
fmap.connect([(mcflirt, tmean,[('out_file','in_file')]),
              (tmean,sink,[('out_file','realignment.@realigned_mean')]),
              ])

# skullstrip magnitude image
bet = Node(fsl.BET(frac=0.6),
           name='bet')
fmap.connect(datasource,'mag', bet,'in_file')
fmap.connect(datasource,'mag', sink,'fieldmap.@mag')

# erode stripped magnitude image further
erode = Node(fsl.maths.ErodeImage(kernel_shape='sphere',
                                 kernel_size=3),
            name='erode')
#erode.iterables=('args', ['','-ero', '-ero -ero'] )
fmap.connect(bet,'out_file', erode, 'in_file')
fmap.connect(erode, 'out_file', sink, 'fieldmap.@masked_mag')

# create binary mask
mask = Node(fsl.maths.UnaryMaths(operation='bin'),
            name='mask')
fmap.connect(erode, 'out_file', mask, 'in_file')
fmap.connect(mask, 'out_file', sink, 'fieldmap.@mag_mask')

# prepare field map
prep_fmap = Node(fsl.epi.PrepareFieldmap(delta_TE=te_diff),
                 name='prep_fmap')
fmap.connect(erode, 'out_file', prep_fmap, 'in_magnitude')
fmap.connect(datasource, 'phase', prep_fmap, 'in_phase')
fmap.connect(prep_fmap, 'out_fieldmap', sink, 'fieldmap.@fmap')

# # unmask fieldmap
# unmask = Node(fsl.FUGUE(unwarp_direction='y-',
#                        save_unmasked_fmap=True,
#                        fmap_out_file='fmap_unmasked.nii.gz'),
#              name='unmask')
# fmap.connect(prep_fmap, 'out_fieldmap', unmask, 'fmap_in_file')
# fmap.connect(mask, 'out_file', unmask,'mask_file')
# fmap.connect(unmask, 'fmap_out_file', sink, 'fieldmap.@fmap_unmasked')
# 
# # unwarp mean epi 
# unwarp = Node(fsl.FUGUE(unwarp_direction='y-',
#                         dwell_time=echo_space,
#                         save_shift=True,),
#               name='unwarp')
# fmap.connect(tmean, 'out_file', unwarp, 'in_file')
# fmap.connect(unmask, 'fmap_out_file', unwarp, 'fmap_in_file')
# fmap.connect(mask, 'out_file', unwarp,'mask_file')
# fmap.connect(unwarp,'unwarped_file',sink,'fieldmap.@unwarped')

fmap.run()