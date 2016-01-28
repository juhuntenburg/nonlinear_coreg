from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util

'''
=============================================================================
CHECK WHICH EPI_T1_NONLINEAR BRANCH YOU ARE ON AND ADAPT THE VERSION VARIABLE
=============================================================================
'''

# nonlinear version
version='version_19'

# directories
out_dir='/scr/kansas1/huntenburg/eval/'+version+'/group/'
working_dir='/scr/kansas1/huntenburg/eval/'+version+'/working_dir/'
mask_dir='/scr/kansas1/huntenburg/eval/'+version+'/'
data_dir='/scr/jessica2/Schaare/LEMON/preprocessed/'
std_brain_mask_dil = '/scr/kansas1/huntenburg/eval/mni/MNI152_T1_1mm_brain_mask_dilM3.nii.gz'

# subjects
subjects=[]
f = open('/scr/jessica2/Schaare/LEMON/done_freesurfer.txt','r')
for line in f:
    subjects.append(line.strip())


# methods
methods=['lin', 'nonlin', 'fmap', 'topup']
contrasts=['nonlin_minus_lin', 'fmap_minus_lin', 'topup_minus_lin', 'fmap_minus_nonlin', 'topup_minus_nonlin', 'fmap_minus_topup']
fields=['nonlin', 'fmap', 'topup']

# create file lists
mean_methodlist=[]
mask_methodlist=[]
for method in methods:
    meanlist=[]
    masklist=[]
    for subject in subjects:
        masklist.append(mask_dir+subject+'/epimask/mni/'+method+'_epimask.nii.gz')
        if method == 'lin':
            meanlist.append(data_dir+subject+'/coreg/lin_mean_norm.nii.gz')
        elif method == 'fmap':
            meanlist.append(data_dir+subject+'/fieldmap_coreg/fmap_mean_norm.nii.gz')
        elif method == 'nonlin':
            meanlist.append(data_dir+subject+'/nonlin_coreg_'+version+'/'+method+'_mean_norm.nii.gz')
        elif method == 'topup':
            meanlist.append(data_dir+subject+'/topup_coreg/'+method+'_mean_norm.nii.gz')
    
    mean_methodlist.append(meanlist)
    mask_methodlist.append(masklist)

diffmap_contrastlist=[]
for contrast in contrasts:
    diffmaplist=[]
    for subject in subjects:
        diffmaplist.append(mask_dir+subject+'/diffmap/mni/'+contrast+'.nii.gz')
    diffmap_contrastlist.append(diffmaplist)
    
# field_methodlist=[]
# for field in fields:
#     fieldlist=[]
#     for subject in subjects:
#         fieldlist.append(mask_dir+subject+'/fieldcompare/fields/'+field+'_field.nii.gz')
#     field_methodlist.append(fieldlist)
#         

'''basic workflow
=======================
'''

# create workflow
group = Workflow(name='group')
group.base_dir=working_dir

# sink
sink = Node(nio.DataSink(base_directory=out_dir,
                         parameterization=False), 
             name='sink')
 

'''groupmeans and sdv
=======================
'''

# merge means
merger = MapNode(fsl.Merge(dimension='t'),
                 iterfield=['in_files'],
                 name='merger')
merger.inputs.in_files=mean_methodlist

# calculate mean of means
meaner = MapNode(fsl.maths.MeanImage(dimension='T'),
                 iterfield=['in_file', 'out_file'],
                 name='meaner')
meaner.inputs.out_file=['lin_groupmean.nii.gz','nonlin_groupmean.nii.gz','fmap_groupmean.nii.gz','topup_groupmean.nii.gz']
group.connect([(merger, meaner, [('merged_file', 'in_file')])])

# mask mean files
mean_masked = MapNode(fsl.BinaryMaths(operation='mul'),
                     iterfield=['in_file', 'out_file'],
                     name='mean_masked')
mean_masked.inputs.out_file=['lin_groupmean.nii.gz','nonlin_groupmean.nii.gz','fmap_groupmean.nii.gz','topup_groupmean.nii.gz']
mean_masked.inputs.operand_file=std_brain_mask_dil
group.connect([(meaner, mean_masked, [('out_file', 'in_file')])])


# calculate sdv of means
sdv = MapNode(fsl.maths.MathsCommand(args='-Tstd'),
                 iterfield=['in_file', 'out_file'],
                 name='sdv')
sdv.inputs.out_file=['lin_groupsdv.nii.gz','nonlin_groupsdv.nii.gz','fmap_groupsdv.nii.gz','topup_groupsdv.nii.gz']
group.connect([(merger, sdv, [('merged_file', 'in_file')])])

# mask sdv file
sdv_masked = mean_masked.clone(name='sdv_masked')
sdv_masked.inputs.out_file=['lin_groupsdv.nii.gz','nonlin_groupsdv.nii.gz','fmap_groupsdv.nii.gz','topup_groupsdv.nii.gz']
sdv_masked.inputs.operand_file=std_brain_mask_dil
group.connect([(sdv, sdv_masked, [('out_file', 'in_file')])])


'''intensity difference
=======================
'''

# merge intensity diffmaps of all subjects for each contrast
diffmap_merger = merger.clone(name='diffmap_merger')
diffmap_merger.inputs.in_files=diffmap_contrastlist

# calculate mean of diffmaps for each contrast
diffmap_meaner=meaner.clone(name='diffmap_meaner')
diffmap_meaner.inputs.out_file=['nonlin_minus_lin.nii.gz', 'fmap_minus_lin.nii.gz', 'topup_minus_lin.nii.gz', 
                                'fmap_minus_nonlin.nii.gz', 'topup_minus_nonlin.nii.gz', 'fmap_minus_topup.nii.gz']

group.connect([(diffmap_merger, diffmap_meaner, [('merged_file', 'in_file')])])


# this doesnt make sense as they are still in indv space, could projec in mni space and then 
#'''deformation fields mean
# ===========================
# '''
# # merger files of all subjects for each method
# field_merger = merger.clone(name='field_merger')
# field_merger.inputs.in_files=field_methodlist
# 
# # calculate mean of that
# field_meaner=meaner.clone(name='field_meaner')
# field_meaner.inputs.out_file=['nonlin_groupfield.nii.gz', 'fmap_groupfield.nii.gz', 'topup_groupfield.nii.gz']
# 
# group.connect([(field_merger, field_meaner, [('merged_file', 'in_file')])])


'''groupmasks: mean, sdv, min/size
==================================
'''
# merge masks
mask_merger=merger.clone(name='mask_merger')
mask_merger.inputs.in_files=mask_methodlist

# calculate mean of masks
mask_meaner = meaner.clone(name='mask_meaner')
mask_meaner.inputs.out_file=['lin_mean_groupmask.nii.gz','nonlin_mean_groupmask.nii.gz','fmap_mean_groupmask.nii.gz','topup_mean_groupmask.nii.gz']
group.connect([(mask_merger, mask_meaner, [('merged_file', 'in_file')])])

# calculate stdev of masks
mask_sdv = sdv.clone(name='mask_sdv')
mask_sdv.inputs.out_file=['lin_sdv_groupmask.nii.gz','nonlin_sdv_groupmask.nii.gz','fmap_sdv_groupmask.nii.gz','topup_sdv_groupmask.nii.gz']
group.connect([(mask_merger, mask_sdv, [('merged_file', 'in_file')])])


# calculate minimal group mask
groupmask=MapNode(fsl.maths.MathsCommand(args='-Tmin'),
                 iterfield=['in_file', 'out_file'],
                 name='groupmask')
groupmask.inputs.out_file=['lin_min_groupmask.nii.gz','nonlin_min_groupmask.nii.gz','fmap_min_groupmask.nii.gz','topup_min_groupmask.nii.gz']

group.connect([(mask_merger, groupmask, [('merged_file', 'in_file')])])

# calculate groupmasksize
masksize = MapNode(fsl.ImageStats(op_string='-V',
                                  output_type='NIFTI_GZ'),
                       iterfield=['in_file'],
                       name='masksize')
 
group.connect([(groupmask, masksize, [('out_file', 'in_file')])])

# write masksizes to file
def write_text(masksizes, filename):
    import numpy as np
    import os
    mask_size_array = np.array(masksizes)
    #mask_size_array=mask_size_array.reshape(np.size(mask_size_array),1)
    np.savetxt(filename, mask_size_array, delimiter=' ', fmt='%f')
    return os.path.abspath(filename)


write_txt = Node(interface=util.Function(input_names=['masksizes', 'filename'],
                                    output_names=['txtfile'],
                                    function=write_text),
              name='write_txt')
write_txt.inputs.filename='min_groupmask_extents.txt'
group.connect([(masksize, write_txt, [('out_stat', 'masksizes')])])


'''connections
=======================
'''

group.connect([(mean_masked, sink, [('out_file', 'groupmeans.@means')]),
               (sdv_masked, sink, [('out_file', 'groupsdv.@sdv')]),
               (diffmap_meaner, sink, [('out_file', 'diffmaps.@diffmaps')]),
               #(field_meaner, sink, [('out_file', 'fields.@fields')]),
               (mask_meaner, sink, [('out_file', 'groupmasks.mean_groupmasks.@masks')]),
               (mask_sdv, sink, [('out_file', 'groupmasks.sdv_groupmasks.@masks')]),
               (groupmask, sink, [('out_file', 'groupmasks.min_groupmasks.@masks')]),
               (write_txt, sink, [('txtfile', 'groupmasks.min_groupmasks.@textfile')])
               ])

# run
group.run(plugin='CondorDAGMan')
    
    
