from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl


def create_diffmap_pipeline(name):
    
    diffmap=Workflow(name=name)

    # inputnode
    inputnode=Node(util.IdentityInterface(fields=['lin_mean',
                                                  'nonlin_mean',
                                                  'fmap_mean',
                                                  'topup_mean',
                                                  'anat_brain']),
                   name='inputnode')
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['diffmaps']),
                    name='outputnode')
    
    
    # create a function and node to get appropriate lists for mapnode
    def make_list(lin, nonlin, fmap, topup):
        in_filelist=[nonlin, fmap, topup, fmap, topup, fmap]
        operand_filelist=[lin, lin, lin, nonlin, nonlin, topup]
        out_filelist=['nonlin_minus_lin.nii.gz','fmap_minus_lin.nii.gz', 'topup_minus_lin.nii.gz', 'fmap_minus_nonlin.nii.gz', 'topup_minus_nonlin.nii.gz', 'fmap_minus_topup.nii.gz']
        
        return in_filelist, operand_filelist, out_filelist
    
    makelist = Node(util.Function(input_names=['lin', 'nonlin', 'fmap', 'topup'],
                                  output_names=['in_filelist', 'operand_filelist','out_filelist'],
                                  function=make_list),
                    name='makelist')
    
    diffmap.connect([(inputnode, makelist, [('lin_mean', 'lin'),
                                            ('nonlin_mean', 'nonlin'),
                                            ('fmap_mean', 'fmap'),
                                            ('topup_mean', 'topup')])])
    
    # calculate diffmaps
    intensity_diff = MapNode(fsl.BinaryMaths(operation='sub'),
                             iterfield=['in_file', 'operand_file'],
                             name='diffmap')

    diffmap.connect([(makelist, intensity_diff, [('in_filelist', 'in_file'),
                                                 ('operand_filelist', 'operand_file')])])
    
    # creat mask from anatomy
    anat_mask = Node(fsl.maths.MathsCommand(args='-bin -fillh'),
                     name='anat_mask')
    
    diffmap.connect([(inputnode, anat_mask, [('anat_brain', 'in_file')])])
    
    # mask diffmaps
    mask_diff = MapNode(fsl.BinaryMaths(operation='mul'),
                        iterfield=['in_file', 'out_file'],
                        name='mask_diff')
    
    diffmap.connect([(intensity_diff, mask_diff, [('out_file', 'in_file')]),
                     (makelist, mask_diff, [('out_filelist', 'out_file')]),
                     (anat_mask, mask_diff, [('out_file', 'operand_file')]),
                     (mask_diff, outputnode, [('out_file', 'diffmaps')])])
    
    return diffmap
    