import numpy as np
import mdtraj as md

all = ["rdf_by_frame"]


def rdf_by_frame(trj, **kwargs):
    """Helper function that computes rdf frame-wise and returns the average
    rdf over all frames. Can be useful for large systems in which a
    distance array of size n_frames * n_atoms (used internally in
    md.compute_rdf) takes requires too much memory.
    """
    g_r = None
    for frame in trj:
        r, g_r_frame = md.compute_rdf(frame, **kwargs)
        if g_r is None:
            g_r = np.zeros_like(g_r_frame)
        g_r += g_r_frame
    g_r /= len(trj)
    return r, g_r


def get_dt(trj):
    """Get the timestep between frames in a MDTraj trajectory."""
    dt = np.unique(np.round(np.diff(trj.time), 3))
    if len(dt) > 1:
        raise ValueError("inconsistent dt")
    else:
        dt = dt[0]

    return dt


def get_unique_atoms(trj):
    """Get mdtraj.Atom objects with unique `name`

    Parameters
    ----------
    trj : MDTraj.trajectory
        trajectory object of system

    Returns
    -------
    unique_atoms : list
        List of unique atoms in trajectory

    """
    seen_atoms = []
    unique_atoms = []
    for atom in trj.topology.atoms:
        if atom.name not in seen_atoms:
            seen_atoms.append(atom.name)
            unique_atoms.append(atom)

    return unique_atoms
