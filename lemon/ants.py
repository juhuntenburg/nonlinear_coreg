from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
import nipype.interfaces.ants as ants
import os

# workflow
normalize=Workflow(name='normalize')

# inputnode
inputnode=Node(util.IdentityInterface(fields=['anat',
                                              'mni']),
               name='inputnode')

# outputnode                                 
outputnode=Node(util.IdentityInterface(fields=['anat2mni_warp',
                                               'anat2mni',
                                               'mni2anat_warp',
                                               'mni2anat']),
                name='outputnode')

# normalization with ants#
antsreg= Node(ants.Registration(dimension=3,
                                transforms=['Rigid','Affine','SyN'],
                                metric=['MI','MI','CC'],
                                metric_weight=[1,1,1],
                                number_of_iterations=[[1000,500,250,100],[1000,500,250,100],[100,70,50,20]],
                                convergence_threshold=[1e-6,1e-6,1e-6],
                                convergence_window_size=[10,10,10],
                                shrink_factors=[[8,4,2,1],[8,4,2,1],[8,4,2,1]],
                                smoothing_sigmas=[[3,2,1,0],[3,2,1,0],[3,2,1,0]],
                                sigma_units=['vox','vox','vox'],
                                initial_moving_transform_com=1,
                                transform_parameters=[(0.1,),(0.1,),(0.1,3.0,0.0)],
                                sampling_strategy=['Regular', 'Regular', 'None'],
                                sampling_percentage=[0.25,0.25,1],
                                radius_or_number_of_bins=[32,32,4],
                                num_threads=1,
                                interpolation='Linear',
                                winsorize_lower_quantile=0.005,
                                winsorize_upper_quantile=0.995,
                                collapse_output_transforms=True,
                                output_inverse_warped_image=True,
                                output_warped_image=True,
                                use_histogram_matching=True,
                                ),
              name='antsreg')
   
#     
#     # function to reduce dimension of ants warp fields from 5 to 4
#     def reduce_deformation_fields(in_file):
#         import nibabel
#         five_d_file = nibabel.load(in_file)
#         data = five_d_file.get_data()
#         four_d_file=nibabel.Nifti1Image(data[:,:,:,0,:], five_d_file.get_affine())
#         nibabel.save(four_d_file, 'reduced.nii.gz')
#         return os.path.abspath('reduced.nii.gz')
#     
#     forward_warp = Node(util.Function(input_names=['in_file', 'out_file'],
#                                  output_names=['out_file'],
#                                  function=reduce_deformation_fields),
#               name='forward_warp')
#     
#     inverse_warp = Node(util.Function(input_names=['in_file', 'out_file'],
#                                  output_names=['out_file'],
#                                  function=reduce_deformation_fields),
#               name='inverse_warp')
#     
#     # functions to return first or second element from list
#     def first_element(file_list):
#         return file_list[0]
#     
#     def second_element(file_list):
#         return file_list[1]

normalize.connect([(inputnode, antsreg, [('anat', 'moving_image'),
                                         ('mni', 'fixed_image')]),
                   (antsreg, outputnode, [('forward_transforms', 'anat2mni_warp'),
                                          ('reverse_transforms', 'mni2anat_warp'),
                                          ('warped_image', 'anat2mni'),
                                          ('inverse_warped_image', 'mni2anat')])
                    ])

#                        (antsreg, outputnode, [(('forward_transforms', first_element), 'anat2mni_affine')]),
#                        (antsreg, outputnode, [(('reverse_transforms', first_element), 'mni2anat_affine')]),
#                        (antsreg, forward_warp, [(('forward_transforms', second_element), 'in_file')]),
#                        (antsreg, inverse_warp, [(('reverse_transforms', second_element), 'in_file')]),
#                        (forward_warp, outputnode, [('out_file', 'anat2mni_warp')]),
#                        (inverse_warp, outputnode, [('out_file', 'mni2anat_warp')])
#                       ])     
    
normalize.base_dir='/scr/kansas1/huntenburg/lemon_missing/working_dir/'
#normalize.config['execution']={'remove_unnecessary_outputs': 'False'}
data_dir='/scr/jessica2/Schaare/LEMON/'
out_dir = '/scr/jessica2/Schaare/LEMON/preprocessed/'
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/missing_subjects.txt','r')
for line in f:
    subjects.append(line.strip())


# infosource to iterate over subjects
infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='infosource')
infosource.iterables=('subject_id', subjects)

# select files
templates={'anat': 'preprocessed/{subject_id}/freesurfer_anatomy/brain_out.nii.gz',
           'mni': 'MNI152_T1_1mm_brain.nii.gz'
           }

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

#sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')
 
# connect to core workflow 
normalize.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
                   (selectfiles, inputnode, [('anat','anat'),
                                             ('mni','mni')]),
                   (infosource, sink, [('subject_id', 'container')]),
                   (outputnode, sink, [('anat2mni', 'normalization.@anat2mni'),
                                       ('anat2mni_warp', 'normalization.@anat2mni_warp'),
                                       ('mni2anat', 'normalization.@mni2anat'),
                                       ('mni2anat_warp', 'normalization.@mni2anat_warp')])
                   ])


normalize.run(plugin='CondorDAGMan')
