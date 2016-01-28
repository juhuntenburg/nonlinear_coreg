#!/bin/bash

data_dir=/scr/jessica2/Schaare/LEMON
new_dir=/scr/jessica2/Schaare/LEMON/raw

for subject in LEMON064 LEMON065 LEMON096 #$(ls $data_dir)

do
	if [[ $subject == *LEMON* ]]
	then
		if [ ! -d "$new_dir/$subject/mp2rage" ]; then
			#mkdir $new_dir/$subject/
			mkdir $new_dir/$subject/mp2rage
			cp $data_dir/$subject/inv1.nii.gz $new_dir/$subject/mp2rage/inv1.nii.gz
			cp $data_dir/$subject/div.nii.gz $new_dir/$subject/mp2rage/div.nii.gz
			cp $data_dir/$subject/*inv2.nii.gz $new_dir/$subject/mp2rage/inv2.nii.gz
			cp $data_dir/$subject/*uni.nii.gz $new_dir/$subject/mp2rage/uni.nii.gz
			cp $data_dir/$subject/*t1.nii.gz $new_dir/$subject/mp2rage/t1.nii.gz

		fi
	fi

done
