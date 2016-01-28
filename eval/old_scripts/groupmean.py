import nipype.interfaces.fsl as fsl
from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.io as nio
from nipype.interfaces import Function


out_dir = '/scr/jessica2/Schaare/LEMON/group_means/'
# create subject list (only those that have normalization)
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
for line in f:
    subjects.append(line.strip())
subjects.remove('LEMON007')
subjects.remove('LEMON027')
subjects.remove('LEMON054')

#create file lists (coregistered and normalized means)
lin_list=[]
for subject in subjects:
    lin_list.append('/scr/jessica2/Schaare/LEMON/preprocessed/'+subject+'/coreg/lin_mean_norm.nii.gz')

nonlin_list=[]
for subject in subjects:
    nonlin_list.append('/scr/jessica2/Schaare/LEMON/preprocessed/'+subject+'/nonlin_coreg/nonlin_mean_norm.nii.gz')
    
fmap_list=[]
for subject in subjects:
    fmap_list.append('/scr/jessica2/Schaare/LEMON/preprocessed/'+subject+'/fieldmap_coreg/fmap_mean_norm.nii.gz')
 
      
topup_list=[]
for subject in subjects:
    topup_list.append('/scr/jessica2/Schaare/LEMON/preprocessed/'+subject+'/topup_coreg/topup_mean_norm.nii.gz')



groupmeans = Workflow(name='means')
groupmeans.base_dir='/scr/kansas1/huntenburg/'
#groupmeans.config['execution']={'remove_unnecessary_outputs': 'False'}

#merge means
lin_merge=Node(fsl.Merge(dimension='t'
                    ),
               name='lin_merge')
lin_merge.inputs.in_files=lin_list


nonlin_merge=Node(fsl.Merge(dimension='t'
                    ),
               name='nonlin_merge')
nonlin_merge.inputs.in_files=nonlin_list

fmap_merge=Node(fsl.Merge(dimension='t'
                    ),
               name='fmap_merge')
fmap_merge.inputs.in_files=fmap_list
 
topup_merge=Node(fsl.Merge(dimension='t'
                    ),
               name='topup_merge')
topup_merge.inputs.in_files=topup_list


#calculate mean of means
lin_tmean = Node(fsl.maths.MeanImage(dimension='T',
                            out_file='lin_groupmean.nii.gz'
                            ),
                 name='lin_tmean')

nonlin_tmean = Node(fsl.maths.MeanImage(dimension='T',
                            out_file='nonlin_groupmean.nii.gz'
                            ),
                 name='nonlin_tmean')

fmap_tmean = Node(fsl.maths.MeanImage(dimension='T',
                            out_file='fmap_groupmean.nii.gz'
                            ),
                 name='fmap_tmean')
 
topup_tmean = Node(fsl.maths.MeanImage(dimension='T',
                            out_file='topup_groupmean.nii.gz'
                            ),
                 name='topup_tmean')

groupmeans.connect([(lin_merge, lin_tmean, [('merged_file', 'in_file')]),
                    (nonlin_merge, nonlin_tmean, [('merged_file', 'in_file')]),
                    (fmap_merge, fmap_tmean, [('merged_file', 'in_file')]),
                    (topup_merge, topup_tmean, [('merged_file', 'in_file')]),
                    ])
 


sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')

groupmeans.connect([(lin_tmean, sink, [('out_file', 'lin_tmean')]),
                    (nonlin_tmean, sink, [('out_file', 'nonlin_tmean')]),
                    (fmap_tmean, sink, [('out_file', 'fmap_tmean')]),
                    (topup_tmean, sink, [('out_file', 'topup_tmean')])
                    ])

groupmeans.run(plugin='CondorDAGMan')


