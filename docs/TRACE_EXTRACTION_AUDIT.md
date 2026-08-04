# Trace Extraction Audit (Feature Pipeline V2)

**Measurement** of candidate/accepted ionospheric trace pixels from the numeric amplitude matrix.

## Stages

1. Column-robust SNR after background score  
2. Vertical interference detection (full-height stripes)  
3. Floor clutter / impulse rejection  
4. Candidate connected components  
5. Ridge-like acceptance (span / aspect)  
6. Centerline via SNR-weighted row per column  
7. Continuity / gap / slope / curvature records  

## Not claimed

- Physical O/X mode identity from Amp_all alone  
- Morphology class (clean / diffuse / frequency / range / mixed)  

## Uncertainty

- `trace_not_found`, `multiple` centerlines, interference overlap, `not_assessable` quality  
- Invalid measurements stay `null` (never coerced to zero)
