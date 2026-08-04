# Local Width Measurement Audit (Feature Pipeline V2)

Global bounding-box width is **not** used as spread evidence.

## Vertical / range-axis width

Per usable frequency column around the centerline; full-height interference columns excluded.

## Horizontal / frequency-axis width

Slope-followed sampling; residual after subtracting thin-ridge geometric width; floor clutter rejected.

## Estimators compared

- FWHM  
- Robust percentile (primary aggregator)  
- Second-moment  
- Connected support  

## Output policy

Each width stores estimator, bins, uncertainty, valid/excluded counts, reason invalid.  
Invalid widths are never averaged into a valid result.

## Classification boundary

Elevated local width is a **measurement**. It is compatible with geometric hypotheses but does **not** prove frequency/range/mixed Spread-F.
