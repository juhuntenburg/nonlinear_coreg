#!/bin/bash

for dwell in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010
do
	echo $dwell
	fugue --in=simulated2fmap_blur2.nii.gz --warp=simulated_distorted_dwell$dwell.nii.gz --loadfmap=fmap_unmasked.nii.gz --dwell=0.$dwell --unwarpdir=y- --nokspace --saveshift=shiftmap_dwell$dwell.nii.gz --smooth3=2

done
