from __future__ import annotations

import numpy as np
import pytest

from ionogram_morphology_lab.importers.mat_inventory import inventory_mat


def test_hdf5_mat_v73_inventory(tmp_path):
    h5py = pytest.importorskip("h5py")
    path = tmp_path / "fake_v73.mat"
    with h5py.File(path, "w") as f:
        f.create_dataset("Amp_all", data=np.zeros((256, 400), dtype=np.float64))
        f.create_dataset("ff", data=np.linspace(1.5, 9.081, 400))
    inv = inventory_mat(path)
    assert inv.adapter == "hdf5_mat_v73"
    assert inv.readable
    assert any(v.name == "Amp_all" for v in inv.variables)
