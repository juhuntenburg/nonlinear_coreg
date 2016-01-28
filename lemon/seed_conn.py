import nipype.interfaces.fsl as fsl
import nipype.interfaces.afni as afni
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
import nipype.pipeline.engine as pe


coordinates = ["S1"]#, "S2", "S3", "I1", "I2","I3"]
sphere_radius_in_mm = 9

def roi2exp(coord, flip, radius):
    coord_dict = {
                   "S1":(-5, -10, 47), 
                   "S3":(-5, 14, 42),
                   "S5":(-5, 34, 28),
                   "S7":(-5, 47, 11),
                   "I9":(-5, 25, -10)}
    coord = coord_dict[coord]
    if flip:
        coord = (-coord[0], coord[1], coord[2])
    return "step(%d-(x%+d)*(x%+d)-(y%+d)*(y%+d)-(z%+d)*(z%+d))"%(radius**2, coord[0], coord[0], coord[1], coord[1], -coord[2], -coord[2])

coordinate_infosource = pe.Node(util.IdentityInterface(fields=["coordinate"]), 
                                name="coordinate_infosource")
coordinate_infosource.iterables = ("coordinate", coordinates)

workflow = pe.Workflow(name="seeding")
workflow.base_dir = "/scr/kansas1/huntenburg/"

sphere_left = pe.Node(afni.Calc(), name="sphere_left")
#sphere_left.inputs.in_file_a = "/home/raid3/jgolchert/Documents/templates/MNI152_T1_3mm_brain.nii.gz" ### individuals brain?
sphere_left.inputs.outputtype = "NIFTI"
sphere_left.inputs.out_file = "roi_point.nii"
workflow.connect(coordinate_infosource, ("coordinate", roi2exp, False, sphere_radius_in_mm), sphere_left, "expr")

sphere_right = sphere_left.clone(name="sphere_right")
workflow.connect(coordinate_infosource, ("coordinate", roi2exp, True, sphere_radius_in_mm), sphere_right, "expr")


combine_left_right = pe.Node(fsl.maths.BinaryMaths(), name="combine_left_right")
combine_left_right.inputs.operation = "max"

def get_out_filename(coordinate):
    return "%s_both_hemi.nii.gz"%coordinate
workflow.connect(coordinate_infosource, ("coordinate", get_out_filename), combine_left_right ,"out_file") 
workflow.connect(sphere_left, "out_file", combine_left_right ,"in_file") 
workflow.connect(sphere_right, "out_file", combine_left_right ,"operand_file") 


datasink = pe.Node(nio.DataSink(), name='sinker')
datasink.inputs.base_directory = '/scr/ilz1/huntenburg/seed_connectivity/'
datasink.inputs.parameterization = True
workflow.connect(combine_left_right, 'out_file', datasink, 'roi')


subject_id_infosource = pe.Node(util.IdentityInterface(fields=["subject_id"]), 
                                name="subject_id_infosource")

subjects = ['LEMON001']#,'LEMON006','LEMON087','LEMON030','LEMON044','LEMON071']
from nipype.utils.misc import human_order_sorted
subjects = human_order_sorted(subjects)
            
subject_id_infosource.iterables = ("subject_id", subjects)


templates={'epi_preproc':'kansas1/huntenburg/preproc/_cor_method_nonlin_ts/_subject_id_{subject_id}/bandpass_filter/nonlin_ts_detrended_regfilt_filt_300_masked.nii.gz',
           'anat_brain':'jessica2/Schaare/LEMON/preprocessed/{subject_id}/freesurfer_anatomy/brain_out.nii.gz'
}


selectfiles = pe.Node(nio.SelectFiles(templates,
                                   base_directory="/scr/"),
                   name="selectfiles")
workflow.connect(selectfiles, "anat_brain", sphere_left, "in_file_a")


#pick first volume
pick_first = pe.Node(fsl.ExtractROI(), name="pick_first")
pick_first.inputs.t_min = 1
pick_first.inputs.t_size = 1
workflow.connect(selectfiles, "epi_preproc", pick_first, "in_file")

#binarize
create_mask = pe.Node(fsl.maths.UnaryMaths(), name="create_mask")
create_mask.inputs.operation = "bin"
workflow.connect(pick_first, "roi_file", create_mask, "in_file")  ## is the pickfirst volume masked?


extract_timeseries = pe.Node(afni.Maskave(), name="extract_timeseries")
extract_timeseries.inputs.quiet = True
workflow.connect(combine_left_right, "out_file", extract_timeseries, "mask")
workflow.connect(selectfiles, "epi_preproc", extract_timeseries, "in_file")


correlation_map = pe.Node(afni.Fim(), name="correlation_map")
correlation_map.inputs.out = "Correlation"
correlation_map.inputs.outputtype = "NIFTI"
correlation_map.inputs.out_file = "corr_map.nii"
workflow.connect(extract_timeseries, "out_file", correlation_map, "ideal_file")
workflow.connect(selectfiles, "epi_preproc", correlation_map, "in_file")


z_trans = pe.Node(interface=afni.Calc(), name='z_trans')
z_trans.inputs.expr = 'log((1+a)/(1-a))/2'
z_trans.inputs.outputtype = 'NIFTI'
workflow.connect(correlation_map, "out_file", z_trans, "in_file_a")

smooth = pe.Node(fsl.maths.IsotropicSmooth(), name = "smooth")
smooth.inputs.fwhm = 6
workflow.connect(z_trans, 'out_file', smooth, "in_file")

#smooth masks
smooth_masks = pe.Node(fsl.maths.IsotropicSmooth(fwhm=6), name="smooth_masks")
workflow.connect(create_mask, "out_file", smooth_masks, "in_file")

#mask the smoothed masks with original binary masks
mask_smooth_masks = pe.Node(fsl.maths.ApplyMask(), name="mask_smooth_masks")
workflow.connect(smooth_masks, "out_file", mask_smooth_masks, "in_file")

#divide smoothed data by the mask smoothed masks
correct_for_border_effects = pe.Node(fsl.maths.BinaryMaths(operation="div"),name="correct_for_border_effects")
workflow.connect(smooth, "out_file", correct_for_border_effects, "in_file")
workflow.connect(mask_smooth_masks, "out_file", correct_for_border_effects, "operand_file")
workflow.connect(correct_for_border_effects, "out_file", datasink, "border_corrected")


workflow.run() #(plugin="Linear", plugin_args={'n_procs' : 2})



