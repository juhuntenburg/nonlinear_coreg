# convert brainweb t1 (default settings noise and rf) to nii
mri_convert t1_icbm_normal_1mm_pn3_rf20.mnc -o t1_brainweb.nii


# register brain to brainweb
flirt -in brain.nii.gz -ref t1_brainweb.nii -out brain2brainweb -dof 6 -omat brain2brainweb.mat


# segment brain2brainweb and merge to 4d file (gm, wm, csf) --> input for possum
fast -n 3 -t 1 -o fast_brainweb brain2brainweb.nii.gz
fslmerge -t brain2brainweb_seg fast_brainweb_pve_1.nii.gz fast_brainweb_pve_2.nii.gz fast_brainweb_pve_0.nii.gz


# register simulated data to fmap
flirt -in simdir/image_abs.nii.gz -ref fmap_mag_1.nii.gz -dof 6 -out simulated2fmap.nii.gz


# blur simulated data
fslmaths simulated2fmap.nii.gz -s 2 simulated2fmap_blur2.nii.gz


# create mask from fieldmap
fslmaths fmap.nii.gz -abs -bin -fillh fmap_mask.nii.gz


# unmask fieldmap
fugue --loadfmap=fmap.nii.gz --savefmap=fmap_unmasked.nii.gz --unmaskfmap --mask=fmap_mask.nii.gz


# apply fieldmap to simulated data (with some smoothing and different echospacing, see distortLoop.sh)

fugue --in=simulated2fmap_blur2.nii.gz --warp=simulated_distorted_dwell0001.nii.gz --loadfmap=fmap_unmasked.nii.gz --dwell=0.0001 --unwarpdir=y- --nokspace --saveshift=shiftmap_dwell0001.nii.gz --smooth3=2


# clip intensities to approx 2x robust range (see clipLoop.sh)

mri_binarize --i simulated_distorted_dwell0005.nii.gz --o bin_simulated_distorted_dwell0005.nii.gz --min 300 --binval 300

fslmaths simulated_distorted_dwell0005.nii.gz -uthr 300 thrs_simulated_distorted_dwell0005.nii.gz

fslmaths thrs_simulated_distorted_dwell0005.nii.gz -add bin_simulated_distorted_dwell0005.nii.gz clipped_simulated_distorted_dwell0005.nii.gz 









