# functions/ — Catalyst Functions

Each subfolder is one deployable Catalyst Function. The CLI picks them up
automatically when you run `catalyst deploy`.

| Function       | Type | Schedule       | Purpose                                            |
|----------------|------|----------------|----------------------------------------------------|
| `ingest_cron/` | Cron | `0 * * * *` IST | Pulls new CSVs from File Store → ingest → datastore |

## Why functions and not just AppSail?

Cron jobs belong on **Functions** (event-driven, scale to zero). The FastAPI
app on AppSail is for synchronous user-facing requests — keeping background
work off it means a busy ingest doesn't slow chat queries.
