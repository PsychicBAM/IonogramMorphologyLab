# Data Formats

Supported input is user-selected MATLAB data in v5/v7 (SciPy path) or v7.3/HDF5 (h5py path), subject to successful audit. Input schema, dimensions, time/frequency axes, orientation and instrument metadata must be reviewed in **Data Audit** and **Instrument Profile**.

Projects retain references and fingerprints rather than modifying sources. Derived Zarr cache, reports, manifests, user rules and exported rule packs are project artifacts. Preserve schema/version information when exchanging them. Do not treat cached arrays or rendered images as an authoritative replacement for original source files.
