#!/bin/bash

# variables
# also adjust paths in dcm2nii
subject=LEMON001
dicom_dir=/scr/jessica2/Schaare/LEMON
out_dir=/scr/ilz1/nonlinear_registration/lemon/testing
echo_space=0.00067
te_diff=0.00246

# create directory
mkdir $out_dir/$subject/

# convert 2 nii (paths need to be adjusted)
# phase image  
dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/rest/fieldmap_2/*
phase_orig=$out_dir/$subject/*004*.nii.gz
# magnitude image: split in two volumes
dcm2nii -d N -4 N -o $out_dir/$subject/ $dicom_dir/$subject/rest/fieldmap_1/*
mag_orig=$out_dir/$subject/*003*_1.nii.gz
# resting state time series
dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/rest/DICOM/*
rest=$out_dir/$subject/*007*.nii.gz

# mcflirt motion correction
mcflirt -in $rest -out $out_dir/$subject/rest_mcf.nii.gz

# calculate tmean
epi_mean=$out_dir/$subject/rest_tmean.nii.gz
fslmaths $out_dir/$subject/rest_mcf.nii.gz -Tmean $epi_mean

# bet on mean epi (easier to see overlap and recommended for undistortion?)
#epi_mean=$out_dir/$subject/rest_tmean_brain.nii.gz
#bet $out_dir/$subject/rest_tmean.nii.gz $epi_mean -f 0.3

# bet on first magnitude image
bet $mag_orig $out_dir/$subject/mag_brain.nii.gz -f 0.6

# erode to make sure no non-brain tissue is contained
mag_brain=$out_dir/$subject/mag_brain_ero.nii.gz
fslmaths $out_dir/$subject/mag_brain.nii.gz -thr 1 -kernel sphere 3 -ero $mag_brain

# create binary mask
mag_mask=$out_dir/$subject/mag_brain_ero_mask.nii.gz
fslmaths $mag_brain -bin $mag_mask

#####################################################
# alternative a: fsl_prepare_fieldmap
fsl_prepare_fieldmap SIEMENS $phase_orig $mag_brain prep_fmap_ero1.nii.gz 2.46
fmap=$out_dir/$subject/prep_fmap_ero1.nii.gz

# alternative b: by hand
# scale phase diff image
# 0 to 360 degrees are mapped to -4096 to 4092, scale to -pi:pi and then *3.14 for radians and mask
#fslmaths $phase_orig -add 2 -div 4094 -mul 3.14159 -mas $mag_mask $out_dir/$subject/phase_rad_brain.nii.gz -odt float
# unwrap
#prelude -p $out_dir/$subject/phase_rad_brain.nii.gz \
#-a $mag_brain -m $mag_mask -o $out_dir/$subject/phase_unwrap.nii.gz
# convert to rad/sec
#phase_radsec=$out_dir/$subject/phase_radsec.nii.gz
#fslmaths $out_dir/$subject/phase_unwrap.nii.gz -div $te_diff $phase_radsec -odt float
# smooth phase image, despike/edges, median filter?
# extrapolate from mask (fill holes)
#fmap=$out_dir/$subject/phase_ex.nii.gz
#fugue --loadfmap=$phase_radsec --mask=$mag_mask --savefmap=$fmap
########################################################

# unmask the fieldmap (avoid edge effects) ####
fugue --loadfmap=$fmap --mask=$mag_mask --unmaskfmap --unwarpdir=y- --savefmap=$out_dir/$subject/phase_unmask.nii.gz
fmap=$out_dir/$subject/phase_unmask.nii.gz

# register mg image to epi
# flirt -in $mag_orig -ref $mean_epi -omat fmap2epi.mat -out mag2epi.nii.gz

# unwarp epi
epi_unwarped=$out_dir/$subject/rest_tmean_unwarped.nii.gz
fugue -i $epi_mean --dwell=$echo_space --unwarpdir=y- --loadfmap=$fmap --saveshift=$out_dir/$subject/pix_shift.nii.gz --mask=$mag_mask -u $epi_unwarped

