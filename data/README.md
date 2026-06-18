# data/

Synthetic sample data for **local dev only**.

- `sample_cases.csv` — 10 fabricated cases. Names, phones, Aadhaar, PAN, vehicle regs are all made up to exercise the PII redactor.

**Do NOT put real KSP data here.** Real data lives in the Catalyst Datastore in production, and never on a developer laptop. The MoU obligates us to keep it that way.

To load this file into the local in-memory datastore:

```bash
python -m services.ingest data/sample_cases.csv
```

Against Catalyst (staging):

```bash
CATALYST_ENABLED=true python -m services.ingest data/sample_cases.csv
```
