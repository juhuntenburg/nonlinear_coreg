#!/bin/bash

for dwell in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010
do
	echo $dwell

	mri_binarize --i simulated_distorted_dwell$dwell.nii.gz --o bin_simulated_distorted_dwell$dwell.nii.gz --min 300 --binval 300

	fslmaths simulated_distorted_dwell$dwell.nii.gz -uthr 300 thrs_simulated_distorted_dwell$dwell.nii.gz

	fslmaths thrs_simulated_distorted_dwell$dwell.nii.gz -add bin_simulated_distorted_dwell$dwell.nii.gz clipped_simulated_distorted_dwell$dwell.nii.gz 

	rm thrs_simulated_distorted_dwell$dwell.nii.gz
	rm bin_simulated_distorted_dwell$dwell.nii.gz

done
