from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.fsl as fsl
import nipype.interfaces.nipy.utils as nutil
import nipype.interfaces.utility as util
from nipype.interfaces import Function
import nipype.interfaces.io as nio
from nipype.algorithms.misc import TSNR
import nipype.algorithms.rapidart as ra

preproc=Workflow(name='preproc')

# outputnode                                     
outputnode=Node(util.IdentityInterface(fields=['noise_mask_file',
                                               'filtered_file']),
                name='outputnode')


###################################################################################################################################
# # artefact detection
# ad = Node(ra.ArtifactDetect(save_plot=False,
#                             norm_threshold=1,
#                             zintensity_threshold=3,
#                             mask_type='spm_global',
#                             use_differences = [True, False],
#                             parameter_source='FSL'),
#           name='artefactdetect')
# 
# #wf.connect(getmask, 'outputspec.mask',ad, 'mask_file') mask_type='file'


###################################################################################################################################
# tsnr (input is timeseries from inputnode)
tsnr = Node(TSNR(regress_poly=2), name='tsnr')
tsnr.plugin_args={'initial_specs': 'request_memory = 30000'}


###################################################################################################################################
# create noise mask file
getthresh = Node(interface=fsl.ImageStats(op_string='-p 98'),
                       name='getthreshold')
getthresh.plugin_args={'initial_specs': 'request_memory = 30000'}

threshold_stddev = Node(fsl.Threshold(), name='threshold')
threshold_stddev.plugin_args={'initial_specs': 'request_memory = 30000'}

preproc.connect(tsnr, 'stddev_file', threshold_stddev, 'in_file')
preproc.connect(tsnr, 'stddev_file', getthresh, 'in_file')
preproc.connect(getthresh, 'out_stat', threshold_stddev, 'thresh')
preproc.connect(threshold_stddev, 'out_file', outputnode, 'noise_mask_file')


###################################################################################################################################
# compcor physiological noise regression
def extract_noise_components(realigned_file, noise_mask_file, num_components):
    """Derive components most reflective of physiological noise
"""
    import os
    from nibabel import load
    import numpy as np
    import scipy as sp
    from scipy import linalg
    from scipy.signal import detrend
    imgseries = load(realigned_file)
    noise_mask = load(noise_mask_file)
    voxel_timecourses = imgseries.get_data()[np.nonzero(noise_mask.get_data())]
    for timecourse in voxel_timecourses:
        timecourse[:] = detrend(timecourse, type='constant')
    u,s,v = linalg.svd(voxel_timecourses, full_matrices=False)
    components_file = os.path.join(os.getcwd(), 'noise_components.txt')
    np.savetxt(components_file, v[:num_components, :].T)
    return components_file


compcor = Node(util.Function(input_names=['realigned_file',
                                          'noise_mask_file',
                                          'num_components'],
                                     output_names=['noise_components'],
                                     function=extract_noise_components),
                       name='compcorr')
compcor.inputs.num_components=6
compcor.plugin_args={'initial_specs': 'request_memory = 30000'}
preproc.connect(threshold_stddev, 'out_file', compcor, 'noise_mask_file')



remove_noise = Node(fsl.FilterRegressor(filter_all=True),
                           name='remove_noise')
    
preproc.connect(tsnr, 'detrended_file',remove_noise, 'in_file')
preproc.connect(compcor, 'noise_components', remove_noise, 'design_file')

###################################################################################################################################
# bandpass filter
# cutoff volumes = 1/(2*TR*cutoff in Hz)
# https://www.jiscmail.ac.uk/cgi-bin/webadmin?A2=ind1205&L=FSL&P=R57592&1=FSL&9=A&I=-3&J=on&d=No+Match%3BMatch%3BMatches&z=4
lp=1./(2*1.4*0.1)
hp=1./(2*1.4*0.01)

bandpass_filter = Node(fsl.TemporalFilter(lowpass_sigma=lp,
                                          highpass_sigma=hp),
                                          name='bandpass_filter')
bandpass_filter.plugin_args={'initial_specs': 'request_memory = 30000'}
             
             
preproc.connect(remove_noise, 'out_file', bandpass_filter, 'in_file')
preproc.connect(bandpass_filter, 'out_file', outputnode, 'filtered_file')


###################################################################################################################################
# in and out
preproc.base_dir='/scr/kansas1/huntenburg/'
preproc.config['execution']={'remove_unnecessary_outputs': 'False'}
out_dir='/scr/'
data_dir='/scr/'
subjects=['LEMON006']#,'LEMON001','LEMON087','LEMON030','LEMON044','LEMON071']


# infosource to iterate over subjects
subject_infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='subject_infosource')
subject_infosource.iterables=('subject_id', subjects)


# infosource to iterate over coregistration methods
cor_method_infosource = Node(util.IdentityInterface(fields=['cor_method']), 
                  name='cor_method_infosource')
cor_method_infosource.iterables=('cor_method', ['lin_ts'])#, 'lin_ts', 'nonlin_ts', 'fmap_ts', 'topup_ts'])


# select files
templates={'timeseries':'kansas1/huntenburg/*_timeseries/_subject_id_{subject_id}/*apply*/{cor_method}.nii.gz',
           #'par_file':'jessica2/Schaare/LEMON/preprocessed/{subject_id}/motion_correction/rest_moco.nii.gz.par'
           }

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")


# store data
# sink = Node(nio.DataSink(base_directory=out_dir,
#                             parameterization=False), 
#                name='sink')

preproc.connect([(subject_infosource, selectfiles, [('subject_id', 'subject_id')]),
                 (cor_method_infosource, selectfiles, [('cor_method', 'cor_method')]),
                 #(infosource, sink, [('subject_id', 'container')]),
                 (selectfiles, tsnr, [('timeseries', 'in_file')]),
                 (selectfiles, compcor, [('timeseries', 'realigned_file')]),
                 ])

preproc.run() #(plugin='CondorDAGMan')
#preproc.write_graph(graph2use='flat', simple_form=False)


