from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import os

#def create_moco_pipeline(name='moco'):
    
# initiate workflow
moco=Workflow(name='moco')

# set fsl output
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

# inputnode
inputnode = Node(util.IdentityInterface(fields=['epi']),
                 name='inputnode')

# outputnode
outputnode = Node(util.IdentityInterface(fields=['epi_moco', 'par_moco', 'mat_moco', 'epi_mean', 'rotplot', 'transplot']),
                  name='outputnode')

# mcflirt motion correction
mcflirt = Node(fsl.MCFLIRT(save_mats=True,
                           save_plots=True,
                           out_file='rest_moco.nii.gz',
                           ref_vol=1
                           ),
               name='mcflirt')

# plot motion parameters
rotplotter = Node(fsl.PlotMotionParams(in_source='fsl',
                               plot_type='rotations',
                               out_file='rotation_plot.png'),
                  name='rotplotter')


transplotter = Node(fsl.PlotMotionParams(in_source='fsl',
                                 plot_type='translations',
                                 out_file='translation_plot.png'),
                    name='transplotter')

# calculate tmean
tmean = Node(fsl.maths.MeanImage(dimension='T',
                                 out_file='rest_moco_mean.nii.gz'),
             name='tmean')

# create connections
moco.connect([(inputnode, mcflirt, [('epi', 'in_file')]),
              (mcflirt, tmean, [('out_file', 'in_file')]),
              (mcflirt, rotplotter, [('par_file', 'in_file')]),
              (mcflirt, transplotter, [('par_file', 'in_file')]),
              (tmean, outputnode, [('out_file', 'epi_mean')]),
              (mcflirt, outputnode, [('out_file','epi_moco'),
                                     ('par_file','par_moco'),
                                     ('mat_file','mat_moco')]),
              (rotplotter, outputnode, [('out_file', 'rotplot')]),
              (transplotter,  outputnode, [('out_file', 'transplot')])
              ])
    
    
    #return moco

######## runningdirectly ####
moco.base_dir='/scr/kansas1/huntenburg/lemon_missing/working_dir/'
data_dir = '/scr/jessica2/Schaare/LEMON/raw/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/missing_subjects.txt','r')
for line in f:
    subjects.append(line.strip())


# create inforsource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# define templates and select files
templates={'epi': '{subject_id}/rest/rest_orig.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

# sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')

# connect to core workflow

moco.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
              (infosource, sink, [('subject_id', 'container')]),
              (selectfiles, inputnode, [('epi', 'epi')]),
              (outputnode, sink, [('epi_moco','motion_correction.@realigned'),
                                  ('par_moco','motion_correction.@par'),
                                  ('mat_moco','motion_correction.MAT.@mat'),
                                  ('epi_mean','motion_correction.@mean'),
                                  ('rotplot', 'motion_correction.@rotplot'),
                                  ('transplot', 'motion_correction.@transplot')])
                      ])

moco.run(plugin='CondorDAGMan')
    
    
    
    