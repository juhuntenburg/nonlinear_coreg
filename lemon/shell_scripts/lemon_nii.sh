#!/bin/bash

dicom_dir=/scr/jessica2/Schaare/LEMON
out_dir=/scr/jessica2/Schaare/LEMON/raw

#for subject in $(ls $out_dir)
for subject in LEMON064 LEMON065 LEMON096

do
	if [[ $subject == *LEMON* ]]
	then
		if [ ! -d "$out_dir/$subject/" ]; then
			
			mkdir $out_dir/$subject/
			mkdir $out_dir/$subject/rest
			dcm2nii -d N -e N -r N -o $out_dir/$subject/rest/ $dicom_dir/$subject/rest/fieldmap_2/*
			mv $out_dir/$subject/rest/grefieldmapping.nii.gz $out_dir/$subject/rest/fmap_phase.nii.gz
			dcm2nii -d N -4 N -e N -r N -o $out_dir/$subject/rest/ $dicom_dir/$subject/rest/fieldmap_1/*
			mv $out_dir/$subject/rest/grefieldmapping_1.nii.gz $out_dir/$subject/rest/fmap_mag_1.nii.gz
			mv $out_dir/$subject/rest/grefieldmapping_2.nii.gz $out_dir/$subject/rest/fmap_mag_2.nii.gz
			dcm2nii -d N -e N -r N -o $out_dir/$subject/rest/ $dicom_dir/$subject/rest/DICOM/*
			mv $out_dir/$subject/rest/cmrrmbep2dresting.nii.gz $out_dir/$subject/rest/rest_orig.nii.gz
			dcm2nii -d N -e N -r N -o $out_dir/$subject/rest/ $dicom_dir/$subject/rest/cmrr_mbep2d_se_before/*
			mv $out_dir/$subject/rest/cmrrmbep2dse.nii.gz $out_dir/$subject/rest/se_1.nii.gz
			dcm2nii -d N -e N -r N -o $out_dir/$subject/rest/ $dicom_dir/$subject/rest/cmrr_mbep2d_se_after/*
			mv $out_dir/$subject/rest/cmrrmbep2dse.nii.gz $out_dir/$subject/rest/se_2.nii.gz
			dcm2nii -d N -e N -r N -o $out_dir/$subject/rest/ $dicom_dir/$subject/rest/cmrr_mbep2d_se_invpol_before/*
			mv $out_dir/$subject/rest/cmrrmbep2dseinvpol.nii.gz $out_dir/$subject/rest/se_inv1.nii.gz
			dcm2nii -d N -e N -r N -o $out_dir/$subject/rest/ $dicom_dir/$subject/rest/cmrr_mbep2d_se_invpol_after/*
			mv $out_dir/$subject/rest/cmrrmbep2dseinvpol.nii.gz $out_dir/$subject/rest/se_inv2.nii.gz

		fi
	fi

done
