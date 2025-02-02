import itertools as it
from progressbar import ProgressBar

import mdtraj as md
import numpy as np
from scipy.integrate import simps

from scattering.utils.utils import rdf_by_frame
from scattering.utils.utils import get_dt
from scattering.utils.constants import get_form_factor


# __all__ = ['structure_factor', 'compute_partial_van_hove', 'compute_van_hove']


def structure_factor(
    trj,
    Q_range=(0.5, 50),
    n_points=1000,
    framewise_rdf=False,
    weighting_factor="fz",
    form="atomic",
):
    """Compute the structure factor through a fourier transform of
    the radial distribution function.

    The consdered trajectory must include valid elements.

    The computed structure factor is only valid for certain values of Q. The
    lowest value of Q that can sufficiently be described by a box of
    characteristic length `L` is `2 * pi / (L / 2)`.

    Parameters
    ----------
    trj : mdtraj.Trajectory
        A trajectory for which the structure factor is to be computed.
    Q_range : list or np.ndarray, default=(0.5, 50)
        Minimum and maximum Values of the scattering vector, in `1/nm`, to be
        consdered.
    n_points : int, default=1000
    framewise_rdf : boolean, default=False
        If True, computes the rdf frame-by-frame. This can be useful for
        managing memory in large systems.
    weighting_factor : string, optional, default='fz'
        Weighting factor for calculating the structure-factor, default is Faber-Ziman.
        See https://openscholarship.wustl.edu/etd/1358/ and http://isaacs.sourceforge.net/manual/page26_mn.html for details.
    form : string, optional, default='atomic'
        Method for determining form factors. If default, form factors are estimated from
        atomic numbers.  If 'cromer-mann', form factors are determined from Cromer-Mann
        tables.

    Returns
    -------
    Q : np.ndarray
        The values of the scattering vector, in `1/nm`, that was considered.
    S : np.ndarray
        The structure factor of the trajectory

    """
    if weighting_factor not in ["fz"]:
        raise ValueError(
            "Invalid weighting_factor `{}` is given."
            "  The only weighting_factor currently supported is `fz`.".format(
                weighting_factor
            )
        )

    rho = np.mean(trj.n_atoms / trj.unitcell_volumes)
    L = np.min(trj.unitcell_lengths)

    top = trj.topology
    elements = set([a.element for a in top.atoms])

    compositions = dict()
    form_factors = dict()
    rdfs = dict()

    Q = np.logspace(np.log10(Q_range[0]), np.log10(Q_range[1]), num=n_points)
    S = np.zeros(shape=(len(Q)))

    for elem in elements:
        compositions[elem.symbol] = (
            len(top.select("element {}".format(elem.symbol))) / trj.n_atoms
        )
        form_factors[elem.symbol] = get_form_factor(
            elem.symbol, q=Q[0] / 10, method=form
        )

    for i, q in enumerate(Q):
        num = 0
        denom = 0

        for elem in elements:
            denom += compositions[elem.symbol] * get_form_factor(
                elem.symbol, q=q / 10, method=form
            )

        for (elem1, elem2) in it.product(elements, repeat=2):
            e1 = elem1.symbol
            e2 = elem2.symbol

            f_a = get_form_factor(e1, q=q / 10, method=form)
            f_b = get_form_factor(e2, q=q / 10, method=form)

            x_a = compositions[e1]
            x_b = compositions[e2]

            try:
                g_r = rdfs["{0}{1}".format(e1, e2)]
            except KeyError:
                pairs = top.select_pairs(
                    selection1="element {}".format(e1),
                    selection2="element {}".format(e2),
                )
                if framewise_rdf:
                    r, g_r = rdf_by_frame(
                        trj, pairs=pairs, r_range=(0, L / 2), bin_width=0.001
                    )
                else:
                    r, g_r = md.compute_rdf(
                        trj, pairs=pairs, r_range=(0, L / 2), bin_width=0.001
                    )
                rdfs["{0}{1}".format(e1, e2)] = g_r
            integral = simps(r ** 2 * (g_r - 1) * np.sin(q * r) / (q * r), r)

            if weighting_factor == "fz":
                pre_factor = 4 * np.pi * rho
                partial_sq = (integral * pre_factor) + 1
                num += (x_a * f_a * x_b * f_b) * (partial_sq)
        S[i] = num / (denom ** 2)
    return Q, S


def compute_dynamic_rdf(trj):
    """Compute r_ij(t), the distance between atom j at time t and atom i and
    time 0. Note that this alone is likely useless, but is an intermediate
    variable in the construction of a dynamic structure factor.
    See 10.1103/PhysRevE.59.623.

    Parameters
    ----------
    trj : mdtraj.Trajectory
        A trajectory for which the structure factor is to be computed

    Returns
    -------
    r_ij : np.ndarray, shape=(trj.n_atoms, trj.n_atoms, trj.n_frames)
        A three-dimensional array of interatomic distances
    """

    n_atoms = trj.n_atoms
    n_frames = trj.n_frames

    r_ij = np.ndarray(shape=(trj.n_atoms, trj.n_atoms, trj.n_frames))

    for n_frame, frame in enumerate(trj):
        for atom_i in range(trj.n_atoms):
            for atom_j in range(trj.n_atoms):
                r_ij[atom_i, atom_j, n_frame] = compute_distance(
                    trj.xyz[n_frame, atom_j], trj.xyz[0, atom_i]
                )

    return r_ij


def compute_distance(point1, point2):
    return np.sqrt(np.sum((point1 - point2) ** 2))


def compute_rdf_from_partial(trj, r_range=None):
    compositions = dict()
    form_factors = dict()
    rdfs = dict()

    L = np.min(trj.unitcell_lengths)
    top = trj.topology
    elements = set([a.element for a in top.atoms])

    denom = 0
    for elem in elements:
        compositions[elem.symbol] = (
            len(top.select("element {}".format(elem.symbol))) / trj.n_atoms
        )
        form_factors[elem.symbol] = elem.atomic_number
        denom += compositions[elem.symbol] * form_factors[elem.symbol]
    for i, (elem1, elem2) in enumerate(it.product(elements, repeat=2)):
        e1 = elem1.symbol
        e2 = elem2.symbol

        x_a = compositions[e1]
        x_b = compositions[e2]

        f_a = form_factors[e1]
        f_b = form_factors[e2]

        try:
            g_r = rdfs["{0}{1}".format(e1, e2)]
        except KeyError:
            pairs = top.select_pairs(
                selection1="element {}".format(e1), selection2="element {}".format(e2)
            )
            if r_range == None:
                r, g_r = md.compute_rdf(trj, pairs=pairs, r_range=(0, L / 2))
            else:
                r, g_r = md.compute_rdf(trj, pairs=pairs, r_range=r_range)
            rdfs["{0}{1}".format(e1, e2)] = g_r
        if i == 0:
            total = g_r * (x_a * x_b * f_a * f_b) / denom ** 2
        else:
            total += g_r * (x_a * x_b * f_a * f_b) / denom ** 2

    return r, total
