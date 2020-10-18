import numpy as np
import nibabel as nb

def py_SurfStatAvVol(filenames, fun = np.add, Nan = None):

    #filenames = file name with extension .mnc, .img, .nii or .brik as above 
    #        (n=1), or n x 1 cell array of file names.

    n = np.shape(filenames)[0]
    file_01 = filenames[0]

    if file_01.endswith('.nii') or file_01.endswith('.nii.gz') or \
        file_01.endswith('.img'):

        if n == 1:
            data_i = np.array(nb.load(file_01).get_fdata())
            m = 1
        else:
            for i in range(0, n):
                d = nb.load(filenames[i])
                data = np.array(d.get_fdata())

                if Nan is not None:
                    data[np.isnan(data)] = Nan

                if i == 0:
                    data_i = data
                    m = 1
                else:
                    if file_01.endswith('.img'):
                        # replace NaN with zeros for proper addition for analyze
                        if fun == np.add:
                            data[np.isnan(data)] = 0
                            data_i[np.isnan(data_i)] = 0
                    data_i = fun(data_i, data)
                    m = fun(m, 1)
    data_i = data_i/float(m)
    vol = {}
    vol['lat'] = np.ones(d.shape[0:3], dtype=bool)
    vol['vox'] = np.array(d.header.get_zooms()[0:3])

    # read the origin from analyze header
    if file_01.endswith('.img'):
        vol['origin'] = d.header['origin'][0:3]
    
    # read the origin from nifti header
    elif file_01.endswith('.nii') or file_01.endswith('.nii.gz'):
        if d.header['qform_code'] > 0:
            origin = [float(d.header['qoffset_x']), float(d.header['qoffset_y']),
                      float(d.header['qoffset_z'])]
        else:
            origin = [d.header['srow_x'][3], d.header['srow_y'][3],
                      d.header['srow_z'][3]]
        vol['origin'] = np.array(origin)

    return data_i, vol

