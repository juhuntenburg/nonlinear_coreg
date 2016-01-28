from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.fsl as fsl
import nipype.interfaces.nipy.utils as nutil
import nipype.interfaces.utility as util
from nipype.interfaces import Function
import nipype.interfaces.io as nio
import nipype.interfaces.afni as afni


diffmap=Workflow(name='diffmap')

# inputnode
inputnode=Node(util.IdentityInterface(fields=['nonlin_mean_coreg',
                                              'fmap_mean_coreg',
                                              'topup_mean_coreg'
                                              ]),
               name='inputnode')

# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['diff_map']),
                name='outputnode')

# make a list
merge_list=Node(util.Merge(2),
                name='merge_list')
 
diffmap.connect([(inputnode, merge_list, [('fmap_mean_coreg','in1'),
                                        ('topup_mean_coreg','in2')])])

# merge topup fmap
merge=Node(fsl.Merge(dimension='t'),
               name='merge')
diffmap.connect([(merge_list,merge,[('out','in_files')])])


# make average topup fmap
average = Node(fsl.maths.MeanImage(dimension='T'),
                 name='average')
diffmap.connect([(merge,average,[('merged_file','in_file')])])


# subtract fmap/topup average from nonlin average
diff_map = Node(fsl.maths.BinaryMaths(operation='sub',
                                      out_file='nonlin_fmaptopup_diffmap.nii.gz'),
                 name='diff_map')
diffmap.connect([(inputnode,diff_map,[('nonlin_mean_coreg','in_file')]),
                 (average, diff_map, [('out_file', 'operand_file')]),
                 (diff_map, outputnode, [('out_file', 'diff_map')])
                 ])


# in and out
diffmap.base_dir='/scr/kansas1/huntenburg/'
out_dir='/scr/jessica2/Schaare/LEMON/preprocessed/'
data_dir='/scr/jessica2/Schaare/LEMON/'
subjects=['LEMON001','LEMON006','LEMON087','LEMON030','LEMON044','LEMON071']


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)


# select files
templates={'nonlin_mean_coreg':'preprocessed/{subject_id}/nonlin_coreg/nonlin_mean_coreg.nii.gz',
           'fmap_mean_coreg':'preprocessed/{subject_id}/fieldmap_coreg/fmap_mean_coreg.nii.gz',
           'topup_mean_coreg':'preprocessed/{subject_id}/topup_coreg/topup_mean_coreg.nii.gz'
}


selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")


sink = Node(nio.DataSink(base_directory=out_dir,
                            parameterization=False), 
               name='sink')

diffmap.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
                 (infosource, sink, [('subject_id', 'container')]),
                 (selectfiles, inputnode, [('nonlin_mean_coreg', 'nonlin_mean_coreg'),
                                           ('fmap_mean_coreg', 'fmap_mean_coreg'),
                                           ('topup_mean_coreg', 'topup_mean_coreg')
                                           ]),
                 (outputnode, sink, [('diff_map', 'diffmap.@diffmap')])
                 ])

diffmap.run(plugin='CondorDAGMan')


