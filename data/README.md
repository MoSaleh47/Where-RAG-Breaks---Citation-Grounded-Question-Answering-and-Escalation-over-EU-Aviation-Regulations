# Data Policy

The new workspace does not copy the historical data automatically. Existing files are referenced through `manifests/` and remain immutable in `../../Documents/`.

Data progression is one-way:

```text
raw source snapshot → interim parse → validated processed corpus → frozen evaluation set
```

Generated files must record:

- source-manifest hash;
- producing script/version;
- configuration path;
- creation timestamp;
- schema version;
- validation status;
- row counts and rejected-row counts.

No generated result should be placed directly in `data/raw/`.

