import numpy as np
import math
from SurfStatEdg import py_SurfStatEdg
from matlab_functions import interp1, ismember
import copy

def py_SurfStatPeakClus(slm, mask, thresh, reselspvert=None, edg=None):
    """ Finds peaks (local maxima) and clusters for surface data.
    Parameters
    ----------
    slm : a dictionary, mandatory keys: 't', 'tri' (or 'lat'),
        optional keys 'df', 'k'.
        slm['t'] : numpy array of shape (l,v),
            v is the number of vertices, the first row slm['t'][0,:] is used
            for the clusters, and the other rows are used to calculate cluster
            resels if slm['k']>1. See SurfStatF for the precise definition
            of the extra rows.
        slm['tri'] : numpy array of shape (t,3), dype=int,
            triangle indices, values should be 1 and v,
        or,
        slm['lat'] : numpy array of shape (nx,nx,nz),
            values should be either 0 or 1.
            note that [nx,ny,nz]=size(volume).
        mask : numpy array of shape (v), dytpe=int,
            values should be either 0 or 1.
        thresh : float,
            clusters are vertices where slm['t'][0,mask]>=thresh.
        reselspvert : numpy array of shape (v),
            resels per vertex, by default: np.ones(v).
        edg :  numpy array of shape (e,2), dtype=int,
            edge indices, by default computed from SurfStatEdg function.
        slm['df'] : int,
            degrees of freedom, note that only the length (1 or 2) is used
            to determine if slm['t'] is Hotelling's T or T^2 when k>1.
        slm['k'] : int,
             k is number of variates, by default 1.

    Returns
    -------
    peak : a dictionary with keys 't', 'vertid', 'clusid'.
        peak['t'] : numpy array of shape (np,1),
            array of peaks (local maxima).
        peak['vertid] : numpy array of shape (np,1),
            array of vertex id's (1-based).
        peak['clusid'] : numpy array of shape (np,1),
            array of cluster id's that contain the peak.
    clus : a dictionary with keys 'clusid', 'nverts', 'resels'.
        clus['clusid'] : numpy array of shape (nc,1),
            array of cluster id numbers.
        clus['nverts'] : numpy array of shape (nc,1),
            array of number of vertices in the cluster.
        clus['resels'] : numpy array of shape (nc,1),
            array of resels in the cluster.
    clusid : numpy array of shape (1,v),
        array of cluster id's for each vertex.
	"""
    if edg is None:
        edg = py_SurfStatEdg(slm)

    l, v = np.shape(slm['t'])
    slm_t = copy.deepcopy(slm['t'])
    slm_t[0, ~mask.astype(bool)] = slm_t[0,:].min()
    t1 = slm_t[0, edg[:,0]]
    t2 = slm_t[0, edg[:,1]]
    islm = np.ones((1,v))
    islm[0, edg[t1 < t2, 0]] = 0
    islm[0, edg[t2 < t1, 1]] = 0
    lmvox = np.argwhere(islm)[:,1] + 1
    excurset = np.array(slm_t[0,:] >= thresh, dtype=int)
    n = excurset.sum()
    
    if n < 1:
        peak = []
        clus = []
        clusid = []
        return peak, clus, clusid

    voxid = np.cumsum(excurset)
    edg = voxid[edg[np.all(excurset[edg],1), :]]
    nf = np.arange(1,n+1)

    # Find cluster id's in nf (from Numerical Recipes in C, page 346):
    for el in range(1, edg.shape[0]+1):
        j = edg[el-1, 0]
        k = edg[el-1, 1]
        while nf[j-1] != j:
            j = nf[j-1]
        while nf[k-1] != k:
            k = nf[k-1]
        if j != k:
            nf[j-1] = k
            
    for j in range(1, n+1):
         while nf[j-1] != nf[nf[j-1]-1]:
             nf[j-1] =  nf[nf[j-1]-1]
 
    vox = np.argwhere(excurset) + 1
    ivox = np.argwhere(np.in1d(vox, lmvox)) + 1  
    clmid = nf[ivox-1]
    uclmid, iclmid, jclmid = np.unique(clmid, 
                                       return_index=True, return_inverse=True)
    iclmid = iclmid +1
    jclmid = jclmid +1
    ucid = np.unique(nf)
    nclus = len(ucid)
    # implementing matlab's histc function ###
    bin_edges   = np.r_[-np.Inf, 0.5 * (ucid[:-1] + ucid[1:]), np.Inf]
    ucvol, ucvol_edges = np.histogram(nf, bin_edges)
    
    if reselspvert is None:
        reselsvox = np.ones(np.shape(vox))
    else:
        reselsvox = reselspvert[vox-1]
        
    # calling matlab-python version for scipy's interp1d
    nf1 = interp1(np.append(0, ucid), np.arange(0,nclus+1), nf, 
                      kind='nearest')
    
    # if k>1, find volume of cluster in added sphere
    if 'k' not in slm or slm['k'] == 1:
        ucrsl = np.bincount(nf1.astype(int), reselsvox.flatten())
    if 'k' in slm and slm['k'] == 2:
        if l == 1:
            ndf = len(np.array([slm['df']]))
            r = 2 * np.arccos((thresh / slm_t[0, vox-1])**(float(1)/ndf))
        else:
            r = 2 * np.arccos(np.sqrt((thresh - slm_t[1,vox-1]) *
                                      (thresh >= slm_t[1,vox-1]) /
                                      (slm_t[0,vox-1] - slm_t[1,vox-1])))
        ucrsl =  np.bincount(nf1.astype(int), (r.T * reselsvox.T).flatten())
    if 'k' in slm and slm['k'] == 3:
        if l == 1:
            ndf = len(np.array([slm['df']]))
            r = 2 * math.pi * (1 - (thresh / slm_t[0, vox-1])**
                                (float(1)/ndf))
        else:
            nt = 20
            theta = (np.arange(1,nt+1,1) - 1/2) / nt * math.pi / 2
            s = (np.cos(theta)**2 * slm_t[1, vox-1]).T
            if l == 3:
                s =  s + ((np.sin(theta)**2) * slm_t[2,vox-1]).T
            r = 2 * math.pi * (1 - np.sqrt((thresh-s)*(thresh>=s) /
                                           (np.ones((nt,1)) *
                                            slm_t[0, vox-1].T -
                                            s ))).mean(axis=0)
        ucrsl = np.bincount(nf1.astype(int), (r.T * reselsvox.T).flatten())
    
    # and their ranks (in ascending order)
    iucrls = sorted(range(len(ucrsl[1:])), key=lambda k: ucrsl[1:][k])
    rankrsl = np.zeros((1, nclus))
    rankrsl[0, iucrls] =  np.arange(nclus,0,-1)
    
    lmid = lmvox[ismember(lmvox, vox)[0]]
       
    varA = slm_t[0, (lmid-1)]
    varB = lmid
    varC = rankrsl[0,jclmid-1]
    varALL = np.concatenate((varA.reshape(len(varA),1),
                             varB.reshape(len(varB),1),
                             varC.reshape(len(varC),1)), axis=1)
    lm = np.flipud(varALL[varALL[:,0].argsort(),])
    varNEW = np.concatenate((rankrsl.T, ucvol.reshape(len(ucvol),1),
                             ucrsl.reshape(len(ucrsl),1)[1:]) , axis=1)
    cl = varNEW[varNEW[:,0].argsort(),]
    clusid = np.zeros((1,v))
    clusid[0,(vox-1).T] = interp1(np.append(0, ucid),
                                      np.append(0, rankrsl), nf,
                                      kind='nearest')
    peak = {}
    peak['t'] = lm[:,0].reshape(len(lm[:,0]), 1)
    peak['vertid'] = lm[:,1].reshape(len(lm[:,1]), 1)
    peak['clusid'] = lm[:,2].reshape(len(lm[:,2]), 1)
    clus = {}
    clus['clusid'] = cl[:,0].reshape(len(cl[:,0]), 1)
    clus['nverts'] = cl[:,1].reshape(len(cl[:,1]), 1) 
    clus['resels'] = cl[:,2] .reshape(len(cl[:,2]), 1)
    
    return peak, clus, clusid
