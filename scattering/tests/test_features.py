import numpy as np
import mdtraj as md

from scattering.utils.io import get_fn
from scattering.utils.features import find_local_maxima, find_local_minima


def test_local_maxima():
    """ Find maxs and mins for O-O RDF of SPC/E water"""
    data = np.loadtxt(get_fn('rdf.txt'))
    r = data[:,0]
    g_r = data[:,1]

    r_maxes = list()
    for i, r_guess in enumerate([0.3, 0.45, 0.65]):
        r_max, g_r_max = find_local_maxima(r, g_r, r_guess=r_guess)
        r_maxes.append(r_max)

    r_mins = list()
    for i, r_guess in enumerate([0.3, 0.5]):
        r_min, g_r_min = find_local_minima(r, g_r, r_guess=r_guess)
        r_mins.append(r_min)
    print(r_mins)

    assert np.allclose(r_maxes, [0.2725, 0.4475, 0.6775])
    assert np.allclose(r_mins, [0.3325, 0.5625])
