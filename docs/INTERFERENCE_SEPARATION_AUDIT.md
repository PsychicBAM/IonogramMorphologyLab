# Interference Separation Audit (Feature Pipeline V2)

Interference is a **separate axis** from morphology.

## Measurements

- Stripe count / width / height persistence / density  
- Affected frequency fraction  
- Overlap with accepted trace  
- Trace pixels remaining outside interference  

## Levels

`none` | `present` | `significant` | `dominant` | `prevents_assessment`

`prevents_assessment` only when usable trace evidence is actually insufficient.  
A frame may simultaneously have an assessable trace, measured diffuseness, and significant interference.

## Classification boundary

Interference diagnostics do **not** replace morphology and do **not** retune RuleEngine.
