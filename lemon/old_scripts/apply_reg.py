#$FSLDIR/bin/applywarp -i ${vepi} -r ${vrefhead} -o ${vout} -w ${vout}_warp --interp=spline --rel

# epireg.connect(epi2anat1, 'out_matrix_file', ---) #${vout}_init.mat
# epireg.connect(fmap2anat2, 'out_matrix_file', ---)#$-omat ${vout}_fieldmap2str.mat 
# epireg.connect(fmap2anat2, 'out_file', ---) # -out ${vout}_fieldmap2str 
# innermask1 'out_file' #${vout}_fieldmaprads2str_pad0
# innermask2 'out_file' #${vout}_fieldmaprads2str_innermask
# epi2anat2 'out_matrix_file' #${vout}.mat
# epi2anat2 'out_file ' #${vout}_1vol
# fmap_dilate 'fmap_out_file' #${vout}_fieldmaprads2str
# wmseg 'out_file' #${vout}_fast_wmseg
# inv_epi2anat 'out_file' #${vout}_inv.mat
# concat_fmapreg 'out_file' #${vout}_fieldmaprads2epi.mat
# fmap2epi 'out_file' #{vout}_fieldmaprads2epi
# fmap_unmask, 'fmap_out_file'# ${vout}_fieldmaprads_unmasked
# fmap_mask2, 'out_file' #${vout}_fieldmaprads2epi_mask
# pixshift 'shift_out_file' #${vout}_fieldmaprads2epi_shift