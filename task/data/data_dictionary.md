# Data dictionary

All scientific probabilities are dimensionless. A,B,M,W,S,Y,X,Z are binary; Y has the recorded label NA exactly when S=0. Only Z,A,W,B,S and recorded Y occur in tables.csv. True X and M and latent U,E are not observed in that file. The probability column is a joint population-limit cell probability, not a count, conditional fraction among viable clones, posterior probability or confidence interval.

contexts.json lists cohort IDs, assay misclassification rates, image_flip, target genotype frequency, rescue resource cost, probability-band halfwidth, and laboratory genotype frequencies. The laboratory populations share the same U|X law within a cohort. Cohorts share the stated model family and decision menu but need not share biological laws.

protocols.json defines which stages are natural or randomized and the exact stagewise randomization probabilities. policies.json contains the entire menu with a indexed by Z and b indexed by [Z][W]. benchmark.json defines the paired-clone comparison policy. study_metadata.json gives identity, numerical acceptance, the operational identification-width cutoff, decision limits and units. data_manifest.json fixes the bytes and SHA-256 of all scientific input files. output_schema.json defines structured output; validate_dataset.py checks integrity, identifiers, event-state domains, cell completeness and probability totals. SOURCE_RIGHTS.md and source_provenance.json record original generation and redistribution basis.

At the task root, required_deliverables.json and deliverables.json are compatibility names for the same three-slot contract. requirements.txt describes supplied runtime dependencies, not a requested solver artifact. There is no finite-sample or bootstrap analysis in this task.
