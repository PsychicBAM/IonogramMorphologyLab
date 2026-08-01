"""Generate tiny synthetic masks for teaching only; outputs are not observations."""
from pathlib import Path
import numpy as np
out=Path(__file__).resolve().parents[1]/"synthetic_data"/"schematics"; out.mkdir(parents=True,exist_ok=True)
for name,axis in {"frequency_spread":1,"range_spread":0,"interference":0}.items():
    mask=np.zeros((48,64),dtype=np.uint8)
    if name=="interference": mask[:,::8]=1
    elif axis: mask[22:27,8:56]=1
    else: mask[8:40,28:33]=1
    np.save(out/f"{name}.npy",mask)
