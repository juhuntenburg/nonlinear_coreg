from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
from mp2rage import create_mp2rage_pipeline
from fieldmap import create_fmap_pipeline
#from topup import create_topup_pipeline
from moco import create_moco_pipeline


mp2rage=create_mp2rage_pipeline()
fmap=create_fmap_pipeline()
#topup=create_topup_pipeline()
moco=create_moco_pipeline()


# variables
#data_dir = '/scr/kalifornien1/data/lemon/lemon_id/'
data_dir = '/scr/kalifornien1/data/lemon/niftis/'
out_dir = '/scr/ilz1/nonlinear_registration/lemon/results/'
subjects=['23197_05']
# subjects = ['LEMON001']
# subjects=os.listdir(data_dir)

# set up main workflow
fmap_topup = Workflow(name='fmap_topup')
fmap_topup.base_dir = '/scr/ilz1/nonlinear_registration/lemon/working_dir'

# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# define templates and select files
templates={'epi': '{subject_id}/cmrrmbep2drestings007a001.nii.gz',
           'mag': '{subject_id}/grefieldmappings003a1001_1.nii.gz',
           'phase': '{subject_id}/grefieldmappings004a2001.nii.gz',
           'se1':'{subject_id}/cmrrmbep2dses005a001.nii.gz',
           'se_inv1':'{subject_id}/cmrrmbep2dseinvpols006a001.nii.gz',
           'se2':'{subject_id}/cmrrmbep2dses008a001.nii.gz',
           'se_inv2':'{subject_id}/cmrrmbep2dseinvpols009a001.nii.gz',
           'inv2':'{subject_id}/mp2ragep3602Bs012a1001.nii.gz',
           't1map':'{subject_id}/mp2ragep3602Bs014a1001.nii.gz',
           'uni':'{subject_id}/mp2ragep3602Bs015a1001.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          substitutions=('_subject_id_', '')), 
             name='sink')

# connections between in and output nodes
fmap_topup.connect([(infosource,selectfiles,[('subject_id','subject_id')]),
                    (infosource, sink,[('subject_id','subject_id')])])
            
# connections between workflows 
fmap_topup.connect([(mp2rage,fmap, [('outputnode.uni_masked', 'inputnode.anat_head'),
                                    ('outputnode.uni_stripped', 'inputnode.anat_brain')]),
                    #(mp2rage,topup, [('outputnode.uni_masked', 'inputnode.anat_head'),
                    #                ('outputnode.uni_stripped', 'inputnode.anat_brain')]),
                    #(moco,fmap,[('outputnode.epi_mean', 'inputnode.epi_mean')]),
                    #(moco,topup,[('outputnode.epi_mean', 'inputnode.epi_mean')]),
                    #(fmap,topup,[('outputnode.wmseg', 'inputnode.wmseg')])
                    ])

# connections from input to workflows
fmap_topup.connect([(selectfiles, mp2rage, [('inv2','inputnode.inv2'),
                                            ('t1map','inputnode.t1map'),
                                            ('uni','inputnode.uni')]),
                    (selectfiles, moco, [('epi','inputnode.epi')]),
                    (selectfiles, fmap, [('mag','inputnode.mag'),
                                         ('phase','inputnode.phase')]),
                    #(selectfiles, topup, [('se1','inputnode.se1'),
                    #                      ('se_inv1','inputnode.se_inv1'),
                     #                     ('se2','inputnode.se2'),
                     #                     ('se_inv2','inputnode.se_inv2')]),
                     #(infosource, topup, [('subject_id', 'bbregister.subject_id')]),
                     #(infosource, fmap, [('subject_id', 'bbregister.subject_id')])
                     ])

# connections from workflows to sink
fmap_topup.connect([(mp2rage, sink, [('outputnode.uni_masked', 'anat.@uni_masked'),
                                     ('outputnode.t1map_masked', 'anat.@t1map_masked'),
                                     ('outputnode.background_mask', 'anat.@background_mask'),
                                     ('outputnode.uni_stripped', 'anat.@uni_stripped'),
                                     ('outputnode.skullstrip_mask', 'anat.@skullstrip_mask')]),
                    (moco,sink,[('outputnode.epi_moco','moco.@epi_moco'),
                               ('outputnode.par_moco','moco.@par_moco'),
                               ('outputnode.mat_moco','moco.@mat_moco'),
                               ('outputnode.epi_mean','moco.@epi_mean')]),
                    (fmap,sink,[('outputnode.wmseg', 'fmap.@wmseg'),
                                ('outputnode.fieldmap','fmap.@fieldmap'),
                                ('outputnode.fmap_shiftmap','fmap.@fmap_shiftmap'),
                                ('outputnode.fmap_epi2anat','fmap.@fmap_epi2anat')]),
                    #(topup,sink,[('outputnode.topup_field', 'topup.@topup_field'),
                    #             ('outputnode.topup_shiftmap', 'topup.@topup_shiftmap'),
                    #             ('outputnode.topup_epi2se', 'topup.@topup_epi2se.mat'),
                     #            ('outputnode.topup_epi2anat', 'topup.@topup_epi2anat.mat')])
                    ])

fmap_topup.run()