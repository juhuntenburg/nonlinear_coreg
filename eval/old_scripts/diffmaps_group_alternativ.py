
# function to read mean images from list output by mapnode
# def list_entry(filelist, index):
#     entry=filelist[index]
#     return entry
# 
# def sublist(filelist, indexstart, indexend):
#     sublist=filelist[indexstart:indexend]
#     return sublist
# 
# 
# # calculating difference to linear coregistration for each method (method-lin)
# diffmap = MapNode(fsl.BinaryMaths(operation='sub'),
#                   iterfield=['in_file'],
#                   name='diffmap')
# 
# group.connect([(meaner, diffmap, [(('out_file', list_entry, 0), 'operand_file')]),
#                 (meaner, diffmap, [('out_file', 'in_file')])])
# 
# # calculating difference between fmap/topup and nonlinear (fmap/topup-nonlinear)
# comparemap = diffmap.clone(name='comparemap')
# 
# group.connect([(meaner, comparemap, [(('out_file', sublist, 2, 4), 'in_file')]),
#                (meaner, comparemap, [(('out_file', list_entry, 1), 'operand_file')])
#                ])
# 
# # mask the difference maps
# mask_diffmaps=MapNode(fsl.BinaryMaths(operation='mul'),
#                      iterfield=['in_file', 'out_file'],
#                      name='mask_diffmaps')
# mask_diffmaps.inputs.operand_file=std_brain_mask_dil
# mask_diffmaps.inputs.out_file= ['lin_minus_lin.nii.gz', 'nonlin_minus_lin.nii.gz', 'fmap_minus_lin.nii.gz', 'topup_minus_lin.nii.gz']
# 
# # mask the compare maps
# mask_comparemaps=mask_diffmaps.clone(name='mask_comparemaps')
# mask_comparemaps.inputs.out_file=['fmap_minus_nonlin.nii.gz', 'topup_minus_nonlin.nii.gz']
# 
# group.connect([(diffmap, mask_diffmaps, [('out_file', 'in_file')]),
#                (comparemap, mask_comparemaps, [('out_file', 'in_file')])])