#!bin/bash/

fmap_ts
fmap_ts_300
nonlin_ts
nonlin_ts_300
resamp_nonlin_ts_300
smooth_resamp_nonlin_ts_300
smooth_fmap_ts_300
corr_map
inv_corr_map
brainmask

fslroi $fmap_ts $fmap_ts_300 0 300
fslroi $nonlin_ts $nonlin_ts_300 0 300

3dResample -master $fmap_ts_300 -prefix $resamp_nonlin_ts_300 -inset $nonlin_ts_300

3dmerge -1blur_fwhm 4.0 -doall -prefix $smooth_fmap_ts_300 $fmap_ts_300
3dmerge -1blur_fwhm 4.0 -doall -prefix $smooth_resamp_nonlin_ts_300 $fmap_resamp_nonlin_ts_300

3dTcorrelate -pearson -prefix $corr_map $smooth_resamp_nonlin_ts_300 $smooth_fmap_ts_300

3dcalc -a $corr_map -expr 'a/(-1)' -prefix $inv_corr_map

resample brainmask and mask inverted images

