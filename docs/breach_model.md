# Breach Hydrograph Model — Rishiganga GLOF, Feb 7 2021

## Model choice
Exponential-rise hydrograph (rise curves upward to peak, then decays).
Rejected trapezoidal (less realistic for a sudden surge) and NWS BREACH
(requires embankment soil/material properties that don't apply — this
event was a rock-ice avalanche, not an earthen dam failure).

## Real data (from published, peer-reviewed sources)
- Peak discharge: ~12,762 m3/s at source
  (Pandey et al. 2023, Natural Hazards, HEC-RAS hydrodynamic modeling)
- Acceptable peak range: 8,200-14,200 m3/s
  (Shugar et al. 2021, Science)
- Avalanche/failure volume: ~27 million m3 of rock and glacier ice
  (Shugar et al. 2021, Science)
- Downstream attenuation (for reference): ~7,900-7,975 m3/s near
  Rishiganga HEP, ~5,780-5,957 m3/s further downstream
  (Pandey et al. 2023)

## Modeling assumptions (not from published sources)
- Rise time to peak: assumed ~10 minutes
- Fall/recession time: assumed ~20 minutes
- Baseline post-event flow: assumed 75 m3/s
(No published rise-time value was found for this event as of this
writing — flagged here for future refinement if better data surfaces.)

## Validation
Peak discharge in our generated hydrograph: 12,762 m3/s -
within the published range of 8,200-14,200 m3/s.

## Sources
- Shugar et al. 2021, "A massive rock and ice avalanche caused the
  2021 disaster at Chamoli, Indian Himalaya," Science.
  https://www.science.org/doi/10.1126/science.abh4455
- Pandey et al. 2023, "Investigation of the flash flood event...
  through hydrodynamic modeling perspectives," Natural Hazards.
  https://link.springer.com/article/10.1007/s11069-023-05972-5