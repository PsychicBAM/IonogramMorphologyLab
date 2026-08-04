# Temporal Feature Audit (Feature Pipeline V2)

Temporal measurements use neighboring **numeric** frames when available.

## Measurements

- Trace-mask overlap  
- Centerline displacement  
- Width / interference / branch persistence  
- Event class labels: sudden appearance/disappearance, gradual onset, continuation, termination, likely isolated artifact  

## Policy

- Stored separately from single-frame measurements  
- Abstain with `temporal_neighbors_unavailable` when neighbors are missing  
- Never silently borrow a neighbor’s morphology classification  

Configurable windows (previous/next one frame, N minutes, selected sequence) are supported at the caller by supplying a `neighbors` list.
