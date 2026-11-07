# Notebooks

Analysis notebooks regenerate FROM VERIFIED RUNS ONLY — never from
in-memory exploratory state. Pattern:

1. `assay run` / `assay analyze` on a config (produces
   `runs/<id>/reports/analysis_report.json` with `report_sha256`).
2. Open the catalog (`runs/<id>/reports/catalog/catalog.sqlite`) or the
   Parquet partitions.
3. Every figure in a notebook carries the provenance stamp (run id,
   config hash, data digest); numbers that cannot be traced to the report
   do not belong in the paper.

The canonical browsing surface is the SQLite catalog
(`assay export --run-dir <run>`): tables `trials`, `verdicts`,
`privileged_index`; views `v_harm_trials`, `v_benign_trials`,
`v_verdict_matrix`.
