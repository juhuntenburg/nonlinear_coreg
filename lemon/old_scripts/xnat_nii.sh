#!/bin/bash

dicom_dir=/scr/kalifornien1/data/lemon/dicoms
out_dir=/scr/kalifornien1/data/lemon/niftis

subject='23197_05'

# for subject in $(ls $dicom_dir)

if [ ! -d "$out_dir/$subject" ]; then
	mkdir $out_dir/$subject/
	dcm2nii -d N -4 N -o $out_dir/$subject/ $dicom_dir/$subject/scans/3/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/4/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/5/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/6/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/7/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/8/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/9/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/12/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/14/DICOM/*
	dcm2nii -d N -o $out_dir/$subject/ $dicom_dir/$subject/scans/15/DICOM/*

fi

