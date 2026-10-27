# Axes and units

NPZ archives are loaded with allow_pickle=False. G is the metadata gene order, P is parental population, A is arm (vehicle then perturbed), T is time order, F is collected fraction (0,1), O is known origin (nucleus then cytoplasm), and R is technical reading.

- observed[G,P,A,T,F]: endogenous hybridization signal; NaN denotes left censoring below limits, never an exact zero.
- limits[P,A,T,F]: detection limits in the same signal units.
- spike_observed[P,A,T,F,O,R]: origin-resolved standard signals; R has two technical readings.
- spike_known[O]: known standard amount per input cell.
- cell_counts[P,A,T]: absolute cell numbers per fixed culture volume. Interval growth is exponential.
- pre_growth[P,A]: independently measured pre-attenuation specific cell growth, inverse hours.
- run_on[P,A,T-1,R]: interval residual transcription relative to the same culture before attenuation, two technical readings. Values apply to each interval, not just its endpoint.

Endogenous signal means are a sample's two-by-two recovery/exposure map multiplied by its physical nuclear/cytoplasmic amounts per cell. Standards identify this map. Metadata gives times in hours, stress membership, the material boundary and measurement error SD. There are six independent biological parents; siblings share parent index across arms.
