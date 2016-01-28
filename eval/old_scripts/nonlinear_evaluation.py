# 
# # calculate masks before and after nonlinear, resample and intersect
# 
# from nipype.interfaces.afni import Automask
# lin_automask = Node(interface=Automask(outputtype='NIFTI_GZ',
#                                        clfrac = 0.6), 
#                     name='automask_after_lin_trans')
# 
# nonreg.connect(lin_epi, 'output_image', lin_automask, 'in_file')
# nonreg.connect(lin_automask, 'out_file', sink, 'eval.automask.lin.@automask')
# 
# nonlin_automask = Node(interface=Automask(outputtype='NIFTI_GZ',
#                                           clfrac = 0.6), 
#                     name='automask_after_nonlin_trans')
# 
# nonreg.connect(nonlin_orig, 'output_image', nonlin_automask, 'in_file')
# nonreg.connect(nonlin_automask, 'out_file', sink, 'eval.automask.nonlin.@automask')
# 
# 
# 
# resamp_lin_mask = Node(interface=Resample(outputtype='NIFTI_GZ',
#                                  voxel_size = (3,3,3)),
#               name = 'resample_lin_automask')
# 
# nonreg.connect(lin_automask, 'out_file', resamp_lin_mask, 'in_file')
# nonreg.connect(resamp_lin_mask,'out_file', sink, 'eval.automask.lin.@resamp')
# 
# resamp_nonlin_mask = Node(interface=Resample(outputtype='NIFTI_GZ',
#                                  voxel_size = (3,3,3)),
#               name = 'resample_nonlin_automask')
# 
# nonreg.connect(nonlin_automask, 'out_file', resamp_nonlin_mask, 'in_file')
# nonreg.connect(resamp_nonlin_mask,'out_file', sink, 'eval.automask.nonlin.@resamp')
# 
# automask_intersect = Node(interface=BinaryMaths(operation='add'), name='automask_intersect')
# 
# nonreg.connect(resamp_lin_mask,'out_file', automask_intersect, 'in_file')
# nonreg.connect(resamp_nonlin_mask,'out_file', automask_intersect, 'operand_file')
# nonreg.connect(automask_intersect, 'out_file', sink, 'eval.automask.intersect.@intersect')
# 
# # <markdowncell>
# 
# # measure mask extens
# 
# # <codecell>
# 
# lin_calc_ext = Node(interface=ImageStats(op_string='-V',
#                                     output_type='NIFTI_GZ'),
#               name='calculate_mask_extents_lin')
# 
# nonreg.connect(lin_automask, 'out_file', lin_calc_ext, 'in_file')
# 
# nonlin_calc_ext = Node(interface=ImageStats(op_string='-V',
#                                     output_type='NIFTI_GZ'),
#               name='calculate_mask_extents_nonlin')
# 
# nonreg.connect(nonlin_automask, 'out_file', nonlin_calc_ext, 'in_file')

# <markdowncell>

# calculate image similarities

# <codecell>

from nipype.interfaces.nipy.utils import Similarity
lin_sim = MapNode(interface = Similarity(),
                  name = 'similarity_lin_trans',
                  iterfield=['metric'])
lin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

nonreg.connect(mriconvert, 'out_file', lin_sim, 'volume1')
nonreg.connect(lin_epi, 'output_image',lin_sim, 'volume2')
nonreg.connect(intersect, 'out_file', lin_sim, 'mask1')


nonlin_sim = MapNode(interface = Similarity(),
                  name = 'similarity_nonlin_trans',
                  iterfield=['metric'])
nonlin_sim.inputs.metric = ['mi','nmi','cc','cr','crl1']

nonreg.connect(mriconvert, 'out_file', nonlin_sim, 'volume1')
nonreg.connect(nonlin_orig, 'output_image',nonlin_sim, 'volume2')
nonreg.connect(intersect, 'out_file', nonlin_sim, 'mask1')

# <markdowncell>

# write values to file

# <codecell>

def write_text(lin_mask_ext, nonlin_mask_ext, lin_metrics, nonlin_metrics):
    import numpy as np
    import os
    #mask = np.array([lin_mask_ext[0], nonlin_mask_ext[0]])
    lin_metrics_array = np.array(lin_metrics)
    lin_mask_array = np.array(lin_mask_ext[0])
    lin_array = np.append(lin_metrics_array,lin_mask_array)
    lin_array=lin_array.reshape(np.size(lin_array),1)
    
    nl_metrics_array = np.array(nonlin_metrics)
    nl_mask_array = np.array(nonlin_mask_ext[0])
    nl_array = np.append(nl_metrics_array,nl_mask_array)
    nl_array=nl_array.reshape(np.size(nl_array),1)
    
    metrics=np.concatenate((lin_array,nl_array),axis=1)
    #mask_file = 'mask_extents.txt'
    metrics_file = 'metrics.txt'
    #np.savetxt(mask_file, mask, delimiter=' ', fmt='%f')
    np.savetxt(metrics_file, metrics, delimiter=' ', fmt='%f')
    return os.path.abspath('metrics.txt') #os.path.abspath('mask_extents.txt'), os.path.abspath('sim_metrics.txt')
    

write_txt = Node(interface=Function(input_names=['lin_mask_ext', 'nonlin_mask_ext','lin_metrics', 'nonlin_metrics'],
                                  output_names=['txtfile'],
                                  function=write_text),
              name='write_file')

nonreg.connect(lin_sim, 'similarity', write_txt, 'lin_metrics')
nonreg.connect(nonlin_sim, 'similarity', write_txt, 'nonlin_metrics')
nonreg.connect(lin_calc_ext, 'out_stat', write_txt, 'lin_mask_ext')
nonreg.connect(nonlin_calc_ext, 'out_stat', write_txt, 'nonlin_mask_ext')
nonreg.connect(write_txt, 'txtfile', sink, 'eval.txt.@txtfile')

# <markdowncell>

# create tsnr maps and calculate differences

# <codecell>

#from nipype.algorithms.misc import TSNR
#lin_tsnr = Node(interface=TSNR(), name='lin_tsnr')

#nonreg.connect(resamp_lin, 'out_file',lin_tsnr,'in_file')
#nonreg.connect(lin_tsnr, 'tsnr_file', sink, 'eval.tsnr.lin.@tsnr')

#nonlin_tsnr = Node(interface=TSNR(), name='nonlin_tsnr')

#nonreg.connect(resamp_nonlin, 'out_file',nonlin_tsnr,'in_file')
#nonreg.connect(nonlin_tsnr, 'tsnr_file', sink, 'eval.tsnr.nonlin.@tsnr')

#sub_tsnr = Node(interface=BinaryMaths(operation='sub'), name='substract_snrs')

#nonreg.connect(nonlin_tsnr, 'tsnr_file', sub_tsnr, 'in_file')
#nonreg.connect(lin_tsnr, 'tsnr_file', sub_tsnr, 'operand_file')
#nonreg.connect(sub_tsnr, 'out_file', sink, 'eval.tsnr.diff.@diff')

#nonreg.connect(lin_tsnr, 'detrended_file', sink, 'eval.tsnr_lin.@detrended')
#nonreg.connect(lin_tsnr, 'mean_file', sink, 'eval.tsnr_lin.@mean')
#nonreg.connect(lin_tsnr, 'stddev_file', sink, 'eval.tsnr_lin.@stddev'

