
test=test10
mkdir /tmp/mp2rage/$test/


cli-run-module de.mpg.cbs.jist.intensity.JistIntensityMp2rageMasking  --inQuantitative /scr/jessica2/Schaare/LEMON/raw/LEMON090/mp2rage/t1.nii.gz --inSecond /scr/jessica2/Schaare/LEMON/raw/LEMON090/mp2rage/inv2.nii.gz --inT1weighted /scr/jessica2/Schaare/LEMON/raw/LEMON090/mp2rage/uni.nii.gz --outMasked /tmp/mp2rage/$test/outMasked.nii --outMasked2 /tmp/mp2rage/$test/outMasked2.nii --outSignal2 /tmp/mp2rage/$test/outSignal2.nii
