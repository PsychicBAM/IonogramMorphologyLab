# IML v1.1 Ionogram Parameters Page Audit

**Application version:** 1.1.0

Every visible parameter has an explicit implementation state. Empty unexplained fields are not shown.

| Parameter | State | Notes |
|---|---|---|
| foE | profile_dependent | Requires E-trace candidate + verified frequency axis |
| h'E | profile_dependent | Nominal virtual height only |
| foEs | profile_dependent | When Es detector fires |
| h'Es | profile_dependent | Nominal virtual height |
| fbEs | source_disabled | Blanketing frequency disabled until source-verified method active |
| foF1 | profile_dependent | Only when F1 separable; else F_unspecified |
| h'F1 | profile_dependent | Nominal virtual height |
| foF2 | profile_dependent | Image-estimated candidate when quality sufficient |
| fxF2 | source_disabled | Not confirmed from Amp_all alone |
| h'F2 | profile_dependent | Nominal virtual height |

Expert actions (accept / reject / indeterminate) apply to catalog rows after load.
