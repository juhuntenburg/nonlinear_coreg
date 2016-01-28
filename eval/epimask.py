from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.utility as util
import nipype.interfaces.afni as afni
import nipype.interfaces.fsl as fsl

def create_epimask_pipeline(name):
    
    epimask=Workflow(name=name)

    # inputnode
    inputnode=Node(util.IdentityInterface(fields=['lin_mean',
                                                  'nonlin_mean',
                                                  'fmap_mean',
                                                  'topup_mean',
                                                  'filename']),
                   name='inputnode')
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['automasks', 
                                                   'textfile']),
                    name='outputnode')
    
    # make list from inputs
    def make_list(lin_mean, nonlin_mean, fmap_mean, topup_mean):
        filelist=[lin_mean, nonlin_mean, fmap_mean, topup_mean]
        return filelist
    
    makelist = Node(util.Function(input_names=['lin_mean', 'nonlin_mean', 'fmap_mean', 'topup_mean'],
                             output_names=['filelist'],
                             function=make_list),
                    name='makelist')
    
    epimask.connect([(inputnode, makelist, [('lin_mean', 'lin_mean'),
                                            ('nonlin_mean', 'nonlin_mean'),
                                            ('fmap_mean', 'fmap_mean'),
                                            ('topup_mean', 'topup_mean')])])

    # calculate automask
    automask = MapNode(fsl.BET(frac=0.4,
                               mask=True),
                       #afni.Automask(outputtype='NIFTI_GZ',
                       #clfrac = 0.6),
                       iterfield=['in_file'],#, 'out_file'],
                       name='automask')
    #automask.inputs.out_file=['lin_automask.nii.gz', 'nonlin_automask.nii.gz', 'fmap_automask.nii.gz', 'topup_automask.nii.gz']
    
    epimask.connect([(makelist, automask, [('filelist', 'in_file')])])
    
    # resample mask
    resampler = MapNode(afni.Resample(voxel_size=(1,1,1),
                                      outputtype='NIFTI_GZ'),
                        iterfield=['in_file', 'out_file'],
                        name='resampler')
    resampler.inputs.out_file=['lin_epimask.nii.gz', 'nonlin_epimask.nii.gz', 'fmap_epimask.nii.gz', 'topup_epimask.nii.gz']
                        
    
    epimask.connect([(automask, resampler, [('mask_file', 'in_file')]),
                     (resampler, outputnode, [('out_file', 'automasks')])])
 

    # measure mask extens
    masksize = MapNode(fsl.ImageStats(op_string='-V',
                                     output_type='NIFTI_GZ'),
                       iterfield=['in_file'],
                       name='masksize')
 
    epimask.connect([(resampler, masksize, [('out_file', 'in_file')])])
    
    
    # write mask extents to file
    def write_text(masksize, filename):
        import numpy as np
        import os
        mask_size_array = np.array(masksize)
        #mask_size_array=mask_size_array.reshape(np.size(mask_size_array),1)
        np.savetxt(filename, mask_size_array, delimiter=' ', fmt='%f')
        return os.path.abspath(filename)
    
    
    write_txt = Node(interface=util.Function(input_names=['masksize', 'filename'],
                                        output_names=['txtfile'],
                                        function=write_text),
                  name='write_txt')
    
    epimask.connect([(masksize, write_txt, [('out_stat', 'masksize')]),
                     (inputnode, write_txt, [('filename', 'filename')]),
                     (write_txt, outputnode, [('txtfile', 'textfile')])])
    
    return epimask