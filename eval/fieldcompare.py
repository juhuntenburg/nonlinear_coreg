from nipype.pipeline.engine import MapNode, Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
from correlation import calc_img_spearmanr
    

def create_fieldcompare_pipeline(name):
    
    fieldcompare = Workflow(name=name)
    
    # inputnode
    inputnode=Node(util.IdentityInterface(fields=['fmap_fmap',
                                                  'topup_fmap',
                                                  'nonlin_deffield',
                                                  'epi_mean',
                                                  'fmap_mag',
                                                  'topup_se1',
                                                  'filename']),
                   name='inputnode')
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['fmap_field',
                                                   'topup_field',
                                                   'nonlin_field', 
                                                   'fieldmask',
                                                   'masked_fields',
                                                   'textfile',
                                                   'min_max_textfile']),
                    name='outputnode')
    
    
    # for topup make mean from se1
    mean_se1=Node(fsl.MeanImage(dimension='T'),
                  name='mean_se1')
    fieldcompare.connect([(inputnode, mean_se1, [('topup_se1', 'in_file')])])
    
    
    # make lists for mapnodes
    def make_list(file1, file2, file3, file4):
        filelist1=[file1, file2]
        filelist2=[file3, file4]
        
        return filelist1, filelist2
    
    makelist = Node(util.Function(input_names=['file1', 'file2', 'file3', 'file4'],
                                  output_names=['filelist1', 'filelist2'],
                                  function=make_list),
                    name='makelist')
    fieldcompare.connect([(inputnode, makelist, [('fmap_fmap', 'file1'),
                                                 ('topup_fmap', 'file2'),
                                                 ('fmap_mag', 'file3')]),
                          (mean_se1, makelist, [('out_file', 'file4')])])
    
    
    # register fieldmaps to epi via ref images
    fmap_ref2epi = MapNode(fsl.FLIRT(dof=6),
                           iterfield=['in_file'],
                           name='fmap_ref2epi')
    fieldcompare.connect([(makelist, fmap_ref2epi, [('filelist2', 'in_file')]),
                          (inputnode, fmap_ref2epi, [('epi_mean', 'reference')])])
    
    fmap2epi = MapNode(fsl.FLIRT(apply_xfm=True,
                              no_search=True),
                       iterfield=['in_file', 'in_matrix_file'],
                       name='fmap2epi')
    
    fieldcompare.connect([(inputnode, fmap2epi, [('epi_mean', 'reference')]),
                          (makelist, fmap2epi, [('filelist1', 'in_file')]),
                          (fmap_ref2epi, fmap2epi, [('out_matrix_file', 'in_matrix_file')])])
    
    
    # derive shiftmaps from the registered fields
    shiftmaps = MapNode(fsl.FUGUE(save_shift=True,
                              dwell_time=0.00067),
                        iterfield=['fmap_in_file', 'unwarp_direction', 'shift_out_file'],
                        name='shiftmaps')
    
    shiftmaps.inputs.shift_out_file=['fmap_shiftmap.nii.gz','topup_shiftmap.nii.gz']
    shiftmaps.inputs.unwarp_direction=['y-','y']
    
    fieldcompare.connect([(fmap2epi, shiftmaps, [('out_file', 'fmap_in_file')])])
    
    # scale shiftmaps from voxels to mm
    scale_fsl = MapNode(fsl.BinaryMaths(operation='mul',
                                   operand_value=2.3),
                    iterfield=['in_file', 'out_file'],
                    name='scale')
    scale_fsl.inputs.out_file=['fmap_field.nii.gz', 'topup_field.nii.gz']
    fieldcompare.connect([(shiftmaps, scale_fsl, [('shift_out_file', 'in_file')])])
    
    # unlist fmap und topup fields
    def unlist(filelist, index):
        return filelist[index]
    
    fieldcompare.connect([(scale_fsl, outputnode, [(('out_file', unlist, 0), 'fmap_field'),
                                               (('out_file', unlist, 1), 'topup_field')])])
    
    
    # make a mask for later correlation from fmap file
    mask = Node(fsl.maths.MathsCommand(args='-abs -bin',
                                 out_file='fieldmask.nii.gz'),
                name='mask')
    
    fieldcompare.connect([(scale_fsl, mask, [(('out_file', unlist, 0), 'in_file')]),
                          (mask, outputnode, [('out_file', 'fieldmask')])])
    
    # reduce ants deformation field to 3D
    def reduce_ants_field(in_file,out_file):
        import nibabel as nb
        import os
        full_file = nb.load(in_file)
        data = full_file.get_data()
        reduced_file=nb.Nifti1Image(data[:,:,:,0,1], full_file.get_affine())
        nb.save(reduced_file, out_file)
        return os.path.abspath(out_file)
    
    reduce_ants = Node(util.Function(input_names=['in_file', 'out_file'],
                                output_names=['out_file'],
                                function=reduce_ants_field),
                  name='reduce_field')
    reduce_ants.inputs.out_file='nonlin_field.nii.gz'
    fieldcompare.connect([(inputnode, reduce_ants, [('nonlin_deffield', 'in_file')]),
                          (reduce_ants, outputnode, [('out_file', 'nonlin_field')])])
    
    
    # make new lists of all three fields
    def make_list2(nonlin_field,fmap_field,topup_field):
        image1_list=[nonlin_field,nonlin_field, fmap_field]
        image2_list=[fmap_field, topup_field, topup_field]
        in_list_masking=[nonlin_field, fmap_field, topup_field]
        return image1_list, image2_list, in_list_masking
    
    makelist2 = Node(util.Function(input_names=['nonlin_field', 'fmap_field', 'topup_field'],
                                  output_names=['image1_list', 'image2_list', 'in_list_masking'],
                                  function=make_list2),
                    name='makelist2')
    
    fieldcompare.connect([(reduce_ants, makelist2, [('out_file', 'nonlin_field')]),
                          (scale_fsl, makelist2, [(('out_file', unlist, 0), 'fmap_field'),
                                                   (('out_file', unlist, 1), 'topup_field')])])
    
    # compute correlations
    corr = MapNode(util.Function(input_names=['image1', 'image2', 'mask'],
                                   output_names=['stats'],
                                   function=calc_img_spearmanr),
                     iterfield=['image1', 'image2'],
                     name='corr')
    
    fieldcompare.connect([(makelist2, corr, [('image1_list', 'image1'),
                                               ('image2_list', 'image2')]),
                          (mask, corr, [('out_file', 'mask')])])
    
    
        

    
    # mask all fields
    mask_fields= MapNode(fsl.ImageMaths(op_string='-mul'),
                      iterfield=['in_file', 'out_file'],
                      name='mask_fields')
    mask_fields.inputs.out_file=['nonlin_field_masked.nii.gz', 'fmap_field_masked.nii.gz', 'topup_field_masked.nii.gz']
    
    fieldcompare.connect([(makelist2, mask_fields, [('in_list_masking', 'in_file')]),
                          (mask, mask_fields, [('out_file', 'in_file2')]),
                          (mask_fields, outputnode, [('out_file', 'masked_fields')])])
    
    
    # calculate robust min max
    min_max = MapNode(fsl.ImageStats(op_string='-r'),
                      iterfield=['in_file'],
                      name='min_max')
    
    fieldcompare.connect([(mask_fields, min_max, [('out_file', 'in_file')])])
    
    
    
    # write textfiles
    def write_text(stats, filename):
        import numpy as np
        import os
        stats_array= np.array(stats)
        np.savetxt(filename, stats_array, delimiter=' ', fmt='%f')
        return os.path.abspath(filename)
    
    write_txt = Node(util.Function(input_names=['stats', 'filename'],
                                      output_names=['txtfile'],
                                      function=write_text),
                     name='write_txt')
    
    
    write_txt_min_max = Node(util.Function(input_names=['stats', 'filename'],
                                           output_names=['txtfile'],
                                           function=write_text),
                             name='write_txt_min_max')
    write_txt_min_max.inputs.filename='min_max.txt'
    
    fieldcompare.connect([(corr, write_txt, [('stats', 'stats')]),
                          (inputnode, write_txt, [('filename', 'filename')]),
                          (write_txt, outputnode, [('txtfile', 'textfile')]),
                          (min_max, write_txt_min_max, [('out_stat' ,'stats')]),
                          (write_txt_min_max, outputnode, [('txtfile', 'min_max_textfile')])
                          ])
    

    
    
    return fieldcompare
