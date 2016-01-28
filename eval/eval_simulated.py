from nipype.pipeline.engine import Node, MapNode, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.nipy.utils as nutil
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
from groundtruth import create_groundtruth_pipeline
from simulation import create_simulation_workflow
from correlation import calc_img_pearsonr, calc_img_spearmanr

'''
=============================================================================
CHECK WHICH EPI_T1_NONLINEAR BRANCH YOU ARE ON AND ADAPT THE VERSION VARIABLE
=============================================================================
'''

# nonlinear version
version='version_19'

''' beware that groundtruth.py and simulation.py are calling epi_t1_nonlinear.py directly
e.g. for version 3 and 4 etc they need to be changed to input normalization transformations and 
fmap mask to the respective sub-workflow'''

# settings
out_dir = '/scr/kansas1/huntenburg/eval/'+version+'/simulated/'
working_dir='/scr/kansas1/huntenburg/eval/'+version+'/working_dir/'
data_dir = '/scr/kansas1/huntenburg/eval/possum/LEMON006/'
freesurfer_dir='/scr/jessica2/Schaare/LEMON/freesurfer/'
freesurfer_id='LEMON006'
dwells=['0001', '0002', '0003', '0004', '0005', '0006', '0007', '0008', '0009', '0010']

# workflow
simulated=Workflow(name='simulated')
simulated.base_dir=working_dir
simulated.config['execution']['crashdump_dir'] = simulated.base_dir + "/crash_files"


# infosource to iterate over different levels of distortion
infosource = Node(util.IdentityInterface(fields=['dwell']), 
                      name='infosource')
infosource.iterables=('dwell', dwells)

# select files
templates={'anat_head':'T1.nii.gz',
           'anat_brain':'brain.nii.gz',
           'anat_brain_mask':'brain_mask.nii.gz',
           'groundtruth':'simulated2fmap_blur2.nii.gz',
           'fmap_mask':'fmap_mask.nii.gz',
           'fmap_unmasked': 'fmap_unmasked.nii.gz',
           'distorted_epi':'clipped_simulated_distorted_dwell{dwell}.nii.gz',
           'shiftmap':'shiftmap_dwell{dwell}.nii.gz',
           'norm_lin':'transform0GenericAffine.mat',
           'norm_invwarp': 'transform1InverseWarp.nii.gz',
           'nonlin_mask': 'fmap_mask_1922_fillh_blur4_bin01_masked.nii.gz'}
    
selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                       name="selectfiles")

simulated.connect([(infosource, selectfiles, [('dwell', 'dwell')])])


# workflow to register groundtruth linearly and nonlinearly to anatomy
groundtruth=create_groundtruth_pipeline(name='groundtruth')
groundtruth.inputs.inputnode.freesurfer_dir=freesurfer_dir
groundtruth.inputs.inputnode.freesurfer_id=freesurfer_id


simulated.connect([(selectfiles, groundtruth, [('fmap_mask', 'inputnode.fmap_mask'),
                                               ('anat_head', 'inputnode.anat_head'),
                                               ('anat_brain', 'inputnode.anat_brain'),
                                               ('anat_brain_mask', 'inputnode.anat_brain_mask'),
                                               ('groundtruth', 'inputnode.epi'),
                                               ('norm_lin', 'inputnode.norm_lin'),
                                                ('norm_invwarp', 'inputnode.norm_invwarp'),
                                                ('nonlin_mask', 'inputnode.nonreg_mask')])])
    


# workflow to perform linear, nonlinear and fmap based coregistration on simulated distorted data
simulation=create_simulation_workflow(name='simulation')
simulation.inputs.inputnode.freesurfer_dir=freesurfer_dir
simulation.inputs.inputnode.freesurfer_id=freesurfer_id
simulated.connect([(infosource, simulation, [('dwell', 'inputnode.dwell')]),
                   (selectfiles, simulation, [('anat_head', 'inputnode.anat_head'),
                                              ('distorted_epi', 'inputnode.distorted_epi'),
                                              ('fmap_mask','inputnode.fmap_mask'),
                                              ('fmap_unmasked','inputnode.fmap_unmasked'),
                                              ('shiftmap','inputnode.shiftmap'),
                                              ('norm_lin', 'inputnode.norm_lin'),
                                              ('norm_invwarp', 'inputnode.norm_invwarp'),
                                              ('nonlin_mask', 'inputnode.nonreg_mask')])])


# correlation of nonlin field to original field
corr_fields = Node(util.Function(input_names=['image1', 'image2', 'mask'],
                                 output_names=['linreg_stats'],
                                 #function = calc_img_linreg,
                                 function = calc_img_spearmanr
                                 ),
                   name='corr_fields')


def write_text(stats, filename):
    import numpy as np
    import os
    stats_array= np.array(stats)
    np.savetxt(filename, stats_array, delimiter=' ', fmt='%f')
    return os.path.abspath(filename)
    
corr_fields_txt = Node(util.Function(input_names=['stats', 'filename'],
                                      output_names=['txtfile'],
                                      function=write_text),
                     name='corr_fields_txt')
corr_fields_txt.inputs.filename='correlation_fields.txt'
simulated.connect([(simulation, corr_fields, [('outputnode.nonlin_field_masked', 'image1'),
                                              ('outputnode.fmap_field_masked', 'image2')]),
                   (selectfiles, corr_fields, [('fmap_mask', 'mask')]),
                   (corr_fields, corr_fields_txt, [('linreg_stats', 'stats')])])


# robust min max of fields
def makelist(file1, file2):
    filelist=[file1,file2]
    return filelist

make_list=Node(util.Function(input_names=['file1', 'file2'],
                             output_names=['filelist'],
                             function=makelist),
               name='make_list')

min_max = MapNode(fsl.ImageStats(op_string='-r'),
                  iterfield=['in_file'],
                  name='min_max')

min_max_txt = corr_fields_txt.clone(name='min_max_txt')
min_max_txt.inputs.filename='min_max_fields.txt'

simulated.connect([(simulation, make_list, [('outputnode.nonlin_field_masked', 'file1'),
                                            ('outputnode.fmap_field_masked', 'file2')]),
                   (make_list, min_max, [('filelist', 'in_file')]),
                   (min_max, min_max_txt, [('out_stat', 'stats')])])



# correlation of different corrections to groundtruth
def makelist2(file1, file2, file3):
    filelist=[file1,file2,file3]
    return filelist

make_list2=Node(util.Function(input_names=['file1', 'file2', 'file3'],
                             output_names=['filelist'],
                             function=makelist2),
               name='make_list2')

corr_epi = MapNode(util.Function(input_names=['image1', 'image2', 'mask'],
                                 output_names=['linreg_stats'],
                                 #function = calc_img_linreg),
                                 function = calc_img_spearmanr),
                   iterfield=['image2'],
                   name='corr_epi')

    
corr_epi_txt = corr_fields_txt.clone(name='corr_epi_txt')
corr_epi_txt.inputs.filename='correlation_groundtruth.txt'

simulated.connect([(simulation, make_list2, [('outputnode.lin_coreg', 'file1'),
                                             ('outputnode.nonlin_coreg', 'file2'),
                                             ('outputnode.fmap_coreg', 'file3')]),
                   (make_list2, corr_epi, [('filelist', 'image2')]),
                   (groundtruth, corr_epi, [('outputnode.lin_coreg', 'image1')]),
                   (selectfiles, corr_epi, [('anat_brain_mask', 'mask')]),
                   (corr_epi, corr_epi_txt, [('linreg_stats', 'stats')])])



# similarity to anatomy
lin_sim = MapNode(interface = nutil.Similarity(),
                  name = 'similarity_lin',
                  iterfield=['metric'])
lin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
nonlin_sim = lin_sim.clone(name='similarity_nonlin')
nonlin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']
fmap_sim = lin_sim.clone(name='similarity_fmap')
fmap_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

def write_simtext(lin_metrics, nonlin_metrics, fmap_metrics, filename):
    import numpy as np
    import os
    lin_array = np.array(lin_metrics)
    lin_array=lin_array.reshape(np.size(lin_array),1)
    nonlin_array = np.array(nonlin_metrics)
    nonlin_array=nonlin_array.reshape(np.size(nonlin_array),1)
    fmap_array = np.array(fmap_metrics)
    fmap_array=fmap_array.reshape(np.size(fmap_array),1)
    metrics=np.concatenate((lin_array, nonlin_array, fmap_array),axis=1)
    metrics_file = filename
    np.savetxt(metrics_file, metrics, delimiter=' ', fmt='%f')
    return os.path.abspath(filename)

write_sim_txt = Node(util.Function(input_names=['lin_metrics', 'nonlin_metrics', 'fmap_metrics', 'filename'],
                                  output_names=['txtfile'],
                                  function=write_simtext),
              name='write_sim_txt')
write_sim_txt.inputs.filename='similarity.txt'

simulated.connect([(selectfiles, lin_sim, [('anat_brain', 'volume1'),
                                           ('anat_brain_mask', 'mask1'),
                                           ('anat_brain_mask', 'mask2')]),
                   (simulation, lin_sim, [('outputnode.lin_coreg', 'volume2')]),
                   (selectfiles, nonlin_sim, [('anat_brain', 'volume1'),
                                           ('anat_brain_mask', 'mask1'),
                                           ('anat_brain_mask', 'mask2')]),
                   (simulation, nonlin_sim, [('outputnode.nonlin_coreg', 'volume2')]),
                   (selectfiles, fmap_sim, [('anat_brain', 'volume1'),
                                           ('anat_brain_mask', 'mask1'),
                                           ('anat_brain_mask', 'mask2')]),
                   (simulation, fmap_sim, [('outputnode.fmap_coreg', 'volume2')]),
                   (lin_sim, write_sim_txt, [('similarity', 'lin_metrics')]),
                   (nonlin_sim, write_sim_txt, [('similarity', 'nonlin_metrics')]),
                   (fmap_sim, write_sim_txt, [('similarity', 'fmap_metrics')])
                   ])


#sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                         parameterization=False),
                name='sink')
      
simulated.connect([(infosource, sink, [('dwell', 'container')]),
                   (groundtruth, sink, [('outputnode.lin_coreg', 'groundtruth.@lin_coreg'),
                                        ('outputnode.nonlin_coreg', 'groundtruth.@nonlin_coreg'),
                                        ('outputnode.nonlin_field', 'groundtruth.@nonlin_field'),
                                        ('outputnode.nonlin_field_masked', 'groundtruth.@nonlin_field_masked'),
                                        ('outputnode.corr_txtfile', 'groundtruth.@corr_txt'),
                                        ('outputnode.sim_txtfile', 'groundtruth.@sim_txt')
                                        ]),
                   (simulation, sink, [('outputnode.lin_coreg', 'corrected.@lin_coreg'),
                                       ('outputnode.nonlin_coreg', 'corrected.@nonlin_coreg'),
                                       ('outputnode.fmap_coreg', 'corrected.@fmap_coreg'),
                                       ('outputnode.nonlin_field', 'fields.@nonlin_field'),
                                       ('outputnode.nonlin_field_masked','fields.@nonlin_field_masked'),
                                       ('outputnode.fmap_field_masked', 'fields.@fmap_field_masked')]),
                   (corr_fields_txt, sink, [('txtfile', 'fields.@correlation_txt')]),
                   (min_max_txt, sink, [('txtfile', 'fields.@min_max_txt')]),
                   (corr_epi_txt, sink, [('txtfile', 'corrected.@correlation_txt')]),
                   (write_sim_txt, sink, [('txtfile', 'corrected.@similarity_txt')])
                   ])

simulated.run(plugin='CondorDAGMan')
