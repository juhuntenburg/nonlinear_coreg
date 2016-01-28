from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl


'''function that calculates spearman correlation of two images within a mask'''
def calc_img_spearmanr(image1, image2, mask):
    import nibabel as nb
    from scipy import stats
    
    # load data
    img1=nb.load(image1).get_data()
    img2=nb.load(image2).get_data()
    mask=nb.load(mask).get_data()
    
    # reduce data to mask
    img1_masked=img1[mask>0]
    img2_masked=img2[mask>0]
    
    # calculate linear regression
    [rho, p] = stats.spearmanr(img1_masked, img2_masked)
    
    return [rho, p]


'''function that calculates voxelwise linear regression of two images within a mask'''
def calc_img_pearsonr(image1, image2, mask):
    import nibabel as nb
    from scipy import stats
    
    # load data
    img1=nb.load(image1).get_data()
    img2=nb.load(image2).get_data()
    mask=nb.load(mask).get_data()
    
    # reduce data to mask
    img1_masked=img1[mask>0]
    img2_masked=img2[mask>0]
    
    # calculate linear regression
    [r,p] = stats.pearsonr(img1_masked, img2_masked)
    
    return [r, p]


'''pipeline to frame it'''
def create_corr_pipeline(name):
    
    correlation=Workflow(name=name)
    
    # inputnode
    inputnode=Node(util.IdentityInterface(fields=['lin_img',
                                                  'nonlin_img',
                                                  'fmap_img',
                                                  'topup_img',
                                                  'filename',
                                                  'brain_or_mask']),
                   name='inputnode')
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['automasks', 
                                                   'textfile']),
                    name='outputnode')
    
    # create list from input for mapnodes
    def make_list(lin_img, nonlin_img, fmap_img, topup_img):
        image1_list=[lin_img, lin_img, lin_img, nonlin_img, nonlin_img, topup_img]
        image2_list=[nonlin_img, fmap_img, topup_img, fmap_img, topup_img, fmap_img]
        return image1_list, image2_list
    
    makelist = Node(util.Function(input_names=['lin_img', 'nonlin_img', 'fmap_img', 'topup_img'],
                             output_names=['image1_list', 'image2_list'],
                             function=make_list),
                    name='makelist')
    
    correlation.connect([(inputnode, makelist, [('lin_img', 'lin_img'),
                                              ('nonlin_img', 'nonlin_img'),
                                              ('fmap_img', 'fmap_img'),
                                              ('topup_img', 'topup_img')])])
    
    # make mask from brainfile
    mask = Node(fsl.maths.MathsCommand(args='-bin -fillh'),
                     name='mask')
    correlation.connect([(inputnode, mask, [('brain_or_mask', 'in_file')])])
    
    # create Function Node to perform linear regression
    corr = MapNode(util.Function(input_names=['image1', 'image2', 'mask'],
                                   output_names=['stats'],
                                   function=calc_img_spearmanr),
                     iterfield=['image1', 'image2'],
                     name='corr')
    
    correlation.connect([(makelist, corr, [('image1_list', 'image1'),
                                             ('image2_list', 'image2')]),
                         (mask, corr, [('out_file', 'mask')])])
    
    
    # write stats to file
    def write_text(stats, filename):
        import numpy as np
        import os
        stats_array= np.array(stats)
        #stats_array=stats_array.reshape(np.size(stats_array),1)
        np.savetxt(filename, stats_array, delimiter=' ', fmt='%f')
        return os.path.abspath(filename)
    
    write_txt = Node(util.Function(input_names=['stats', 'filename'],
                                      output_names=['txtfile'],
                                      function=write_text),
                     name='write_txt')
    
    correlation.connect([(corr, write_txt, [('stats', 'stats')]),
                         (inputnode, write_txt, [('filename', 'filename')]),
                         (write_txt, outputnode, [('txtfile', 'textfile')])])

    return correlation
