from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
from similarity import create_similarity_pipeline
from epimask import create_epimask_pipeline
from diffmap import create_diffmap_pipeline
from correlation import create_corr_pipeline
from fieldcompare import create_fieldcompare_pipeline

'''
=============================================================================
CHECK WHICH EPI_T1_NONLINEAR BRANCH YOU ARE ON AND ADAPT THE VERSION VARIABLE
=============================================================================
'''

# nonlinear version
version='version_19'


# set directories etc
out_dir='/scr/kansas1/huntenburg/eval/'+version+'/'
working_dir='/scr/kansas1/huntenburg/eval/'+version+'/working_dir'
data_dir='/scr/jessica2/Schaare/LEMON/'
std_brain = '/scr/kansas1/huntenburg/eval/mni/MNI152_T1_1mm_brain.nii.gz'
std_brain_mask = '/scr/kansas1/huntenburg/eval/mni/MNI152_T1_1mm_brain_mask.nii.gz'
std_ofc_mask = '/scr/kansas1/huntenburg/eval/mni/Harvard_Oxford_frontal_orbital_thr_25.nii.gz'

subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
for line in f:
    subjects.append(line.strip())





# workflow
evaluation = Workflow(name='evaluation')
evaluation.base_dir = working_dir

# infosource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                      name='infosource')
infosource.iterables=('subject_id', subjects)

# get data in here
templates={'anat_head':'preprocessed/{subject_id}/freesurfer_anatomy/T1_out.nii.gz',
           'anat_brain':'preprocessed/{subject_id}/freesurfer_anatomy/brain_out.nii.gz',
           'moco_mean':'preprocessed/{subject_id}/motion_correction/rest_moco_mean.nii.gz',
           'lin_mean_coreg':'preprocessed/{subject_id}/coreg/lin_mean_coreg.nii.gz',
           'lin_mean_norm':'preprocessed/{subject_id}/coreg/lin_mean_norm.nii.gz',
           'nonlin_mean_coreg':'preprocessed/{subject_id}/nonlin_coreg_'+version+'/nonlin_mean_coreg.nii.gz',
           'nonlin_mean_norm':'preprocessed/{subject_id}/nonlin_coreg_'+version+'/nonlin_mean_norm.nii.gz',
           'nonlin_deffield':'preprocessed/{subject_id}/nonlin_coreg_'+version+'/transform1InverseWarp.nii.gz',
           'fmap_mean_coreg':'preprocessed/{subject_id}/fieldmap_coreg/fmap_mean_coreg.nii.gz',
           'fmap_mean_norm':'preprocessed/{subject_id}/fieldmap_coreg/fmap_mean_norm.nii.gz',
           'fmap_fmap':'preprocessed/{subject_id}/fieldmap_coreg/fmap_phase_fslprepared.nii.gz',
           'fmap_mag':'raw/{subject_id}/rest/fmap_mag_1.nii.gz',
           'topup_mean_coreg':'preprocessed/{subject_id}/topup_coreg/topup_mean_coreg.nii.gz',
           'topup_mean_norm':'preprocessed/{subject_id}/topup_coreg/topup_mean_norm.nii.gz',
           'topup_fmap':'preprocessed/{subject_id}/topup_coreg/topup_fmap.nii.gz',
           'topup_se1':'raw/{subject_id}/rest/se_1.nii.gz'
}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

evaluation.connect([(infosource, selectfiles, [('subject_id', 'subject_id')])])


# calculate similarities to the mni brain for all methods
similarity_mni_brain=create_similarity_pipeline(name='similarity_mni_brain')
similarity_mni_brain.inputs.inputnode.anat_brain=std_brain
similarity_mni_brain.inputs.inputnode.mask=std_brain_mask
similarity_mni_brain.inputs.inputnode.filename='metrics_mni_brain.txt'
  
evaluation.connect([(selectfiles, similarity_mni_brain, [('lin_mean_norm', 'inputnode.lin_mean'),
                                                         ('nonlin_mean_norm', 'inputnode.nonlin_mean'),
                                                         ('fmap_mean_norm', 'inputnode.fmap_mean'),
                                                         ('topup_mean_norm', 'inputnode.topup_mean')])])
                     
# calculate similarities to mni within ofc mask for all methods
similarity_mni_ofc=create_similarity_pipeline(name='similarity_mni_ofc')
similarity_mni_ofc.inputs.inputnode.anat_brain=std_brain
similarity_mni_ofc.inputs.inputnode.mask=std_ofc_mask
similarity_mni_ofc.inputs.inputnode.filename='metrics_mni_ofc.txt'
   
evaluation.connect([(selectfiles, similarity_mni_ofc, [('lin_mean_norm', 'inputnode.lin_mean'),
                                                       ('nonlin_mean_norm', 'inputnode.nonlin_mean'),
                                                       ('fmap_mean_norm', 'inputnode.fmap_mean'),
                                                       ('topup_mean_norm', 'inputnode.topup_mean')])])
     


# calculate automasks in individual space and mask extents
epimask_indv = create_epimask_pipeline(name='epimask_indv')
epimask_indv.inputs.inputnode.filename='epimask_extents_indv.txt'

evaluation.connect([(selectfiles, epimask_indv, [('lin_mean_coreg', 'inputnode.lin_mean'),
                                                 ('nonlin_mean_coreg', 'inputnode.nonlin_mean'),
                                                 ('fmap_mean_coreg', 'inputnode.fmap_mean'),
                                                 ('topup_mean_coreg', 'inputnode.topup_mean')])])


# calculate automasks in standard space and mask extents
epimask_mni = create_epimask_pipeline(name='epimask_mni')
epimask_mni.inputs.inputnode.filename='epimask_extents_mni.txt'

evaluation.connect([(selectfiles, epimask_mni, [('lin_mean_norm', 'inputnode.lin_mean'),
                                            ('nonlin_mean_norm', 'inputnode.nonlin_mean'),
                                            ('fmap_mean_norm', 'inputnode.fmap_mean'),
                                            ('topup_mean_norm', 'inputnode.topup_mean')])])


# calculate intensity difference maps in indv and mni space
diffmap_indv = create_diffmap_pipeline(name='diffmap_indv')
diffmap_mni = create_diffmap_pipeline(name='diffmap_mni')
diffmap_mni.inputs.inputnode.anat_brain=std_brain

evaluation.connect([(selectfiles, diffmap_indv, [('lin_mean_coreg', 'inputnode.lin_mean'),
                                                 ('nonlin_mean_coreg', 'inputnode.nonlin_mean'),
                                                 ('fmap_mean_coreg', 'inputnode.fmap_mean'),
                                                 ('topup_mean_coreg', 'inputnode.topup_mean'),
                                                 ('anat_brain', 'inputnode.anat_brain')]),
                    (selectfiles, diffmap_mni, [('lin_mean_norm', 'inputnode.lin_mean'),
                                                 ('nonlin_mean_norm', 'inputnode.nonlin_mean'),
                                                 ('fmap_mean_norm', 'inputnode.fmap_mean'),
                                                 ('topup_mean_norm', 'inputnode.topup_mean')])
                                                 ])


# calculate image correlations on individual level
corr_indv = create_corr_pipeline(name='corr_indv')
corr_indv.inputs.inputnode.filename='mean_correlation_indv.txt'

evaluation.connect([(selectfiles, corr_indv, [('lin_mean_coreg', 'inputnode.lin_img'),
                                                ('nonlin_mean_coreg', 'inputnode.nonlin_img'),
                                                ('fmap_mean_coreg', 'inputnode.fmap_img'),
                                                ('topup_mean_coreg', 'inputnode.topup_img'),
                                                ('anat_brain', 'inputnode.brain_or_mask')])
                     ])

# calculate image correlations in mni space
corr_mni = create_corr_pipeline(name='corr_mni')
corr_mni.inputs.inputnode.filename='mean_correlation_mni.txt'
corr_mni.inputs.inputnode.brain_or_mask=std_brain

evaluation.connect([(selectfiles, corr_mni, [('lin_mean_norm', 'inputnode.lin_img'),
                                              ('nonlin_mean_norm', 'inputnode.nonlin_img'),
                                              ('fmap_mean_norm', 'inputnode.fmap_img'),
                                              ('topup_mean_norm', 'inputnode.topup_img')])
                     ])

# calculate image correlations in ofc in mni space
corr_mni_ofc = create_corr_pipeline(name='corr_mni_ofc')
corr_mni_ofc.inputs.inputnode.filename='mean_correlation_mni_ofc.txt'
corr_mni_ofc.inputs.inputnode.brain_or_mask=std_ofc_mask

evaluation.connect([(selectfiles, corr_mni_ofc, [('lin_mean_norm', 'inputnode.lin_img'),
                                                 ('nonlin_mean_norm', 'inputnode.nonlin_img'),
                                                 ('fmap_mean_norm', 'inputnode.fmap_img'),
                                                 ('topup_mean_norm', 'inputnode.topup_img')])
                     ])



# derive comparable deformation fields and calculate their correlation
fieldcompare=create_fieldcompare_pipeline(name='fieldcompare')
fieldcompare.inputs.inputnode.filename='field_correlation_indv.txt'

evaluation.connect([(selectfiles, fieldcompare, [('nonlin_deffield', 'inputnode.nonlin_deffield'),
                                                 ('fmap_fmap', 'inputnode.fmap_fmap'),
                                                 ('topup_fmap', 'inputnode.topup_fmap'),
                                                 ('moco_mean', 'inputnode.epi_mean'),
                                                 ('fmap_mag', 'inputnode.fmap_mag'),
                                                 ('topup_se1', 'inputnode.topup_se1')])])


# sink to store results
sink = Node(nio.DataSink(base_directory=out_dir,
                            parameterization=False), 
               name='sink')
  
evaluation.connect([(infosource, sink, [('subject_id', 'container')]),
                    (similarity_mni_brain, sink,[('outputnode.textfile', 'similarity.@mni_brain_txtfile')]),
                    (similarity_mni_ofc, sink,[('outputnode.textfile', 'similarity.@mni_ofc_txtfile')]),
                    (epimask_indv, sink, [('outputnode.automasks', 'epimask.indv.@epimasks'),
                                          ('outputnode.textfile', 'epimask.indv.@textfile')]),
                    (epimask_mni, sink, [('outputnode.automasks', 'epimask.mni.@epimasks'),
                                          ('outputnode.textfile', 'epimask.mni.@textfile')]),
                    (diffmap_indv, sink, [('outputnode.diffmaps', 'diffmap.indv.@diffmaps')]),
                    (diffmap_mni, sink, [('outputnode.diffmaps', 'diffmap.mni.@diffmaps')]),
                    (corr_indv, sink, [('outputnode.textfile', 'correlation.indv.@txtfile')]),
                    (corr_mni, sink, [('outputnode.textfile', 'correlation.mni.@txtfile')]),
                    (corr_mni_ofc, sink, [('outputnode.textfile', 'correlation.mni_ofc.@txtfile')]),
                    (fieldcompare, sink, [('outputnode.nonlin_field', 'fieldcompare.fields.@nonlin'),
                                          ('outputnode.fmap_field', 'fieldcompare.fields.@fmap'),
                                          ('outputnode.topup_field', 'fieldcompare.fields.@topup'),
                                          ('outputnode.fieldmask', 'fieldcompare.fields.@mask'),
                                          ('outputnode.masked_fields', 'fieldcompare.fields.@masked_fields'),
                                          ('outputnode.textfile', 'fieldcompare.@txtfile'),
                                          ('outputnode.min_max_textfile', 'fieldcompare.@min_max_txtfile')])
                    ])

evaluation.write_graph(dotfilename='eval_subject.dot', graph2use='colored', format='pdf', simple_form=True)
evaluation.run(plugin='CondorDAGMan')
