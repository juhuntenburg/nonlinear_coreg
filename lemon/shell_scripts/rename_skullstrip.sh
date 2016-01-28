#!/bin/bash

data_dir=/scr/jessica2/Schaare/LEMON/preprocessed
counter=0

for subject in LEMON064 LEMON065 LEMON096 #$(ls $data_dir)

do
	if [[ $subject == *LEMON* ]]
	then
		if [ -d "$data_dir/$subject/" ]; then
			mv $data_dir/$subject/background_masking/outMasked.nii $data_dir/$subject/background_masking/t1_masked.nii		
			mv $data_dir/$subject/background_masking/outMasked2.nii $data_dir/$subject/background_masking/uni_masked.nii
			mv $data_dir/$subject/background_masking/outSignal2.nii $data_dir/$subject/background_masking/background_mask.nii
			mv $data_dir/$subject/skullstrip/outStripped.nii $data_dir/$subject/skullstrip/uni_stripped.nii
			mv $data_dir/$subject/skullstrip/outMask.nii $data_dir/$subject/skullstrip/skullstrip_mask.nii
			mv $data_dir/$subject/skullstrip/outOriginal.nii $data_dir/$subject/skullstrip/uni_reoriented.nii
			
			subjects[$counter]=$subject
                	counter=$(($counter+1))

		fi
	fi

done

echo ${subjects[@]}
echo ${#subjects[@]}


