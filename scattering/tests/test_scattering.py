import numpy as np
import matplotlib.pyplot as plt
import mdtraj as md
import pytest

from scattering.scattering import structure_factor
from scattering.utils.io import get_fn

@pytest.mark.parametrize('weighting_factor', ['fz'])
def test_structure_factor(weighting_factor):
    trj = md.load(
        get_fn('spce.xtc'),
        top=get_fn('spce.gro')
    )[:100]

    Q, S = structure_factor(trj,
                            Q_range=(0.5, 200),
                            framewise_rdf=False,
                            weighting_factor=weighting_factor)

def test_invalid_sq_weigting_factor():
    trj = md.load(
        get_fn('spce.xtc'),
        top=get_fn('spce.gro')
    )[:100]

    with pytest.raises(ValueError):
        Q, S = structure_factor(trj,
                                Q_range=(0.5, 200),
                                framewise_rdf=False,
                                weighting_factor='invalid')
