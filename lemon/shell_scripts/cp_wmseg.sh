#!/bin/bash

subjects_dir=/scr/jessica2/Schaare/LEMON/freesurfer/freesurfer
preprocessed_dir=/scr/jessica2/Schaare/LEMON/preprocessed

for subject in LEMON013 #$(ls $data_dir)
do
	if [[ $subject == *LEMON* ]]
	then
		cp $preprocessed_dir/$subject/coreg/wmseg.nii.gz $preprocessed_dir/$subject/freesurfer_anatomy/brain_out_wmseg.nii.gz
	fi

done

