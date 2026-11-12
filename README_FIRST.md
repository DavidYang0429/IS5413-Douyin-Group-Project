# IS5413 Final Submission

Team: Save 50 pounds

The final report is **交付物/IS5413_Final_Report_Douyin.docx** in this public checkout. It has 16 pages, including the model, physical design, ten SELECT tasks with actual results, transaction implementation and verification evidence.

The working prototype uses Python 3.10+ and a real Supabase PostgreSQL 17 database. It is a local demonstration, not a public hosted website. The initial design remains ten business tables and 43 columns.

## Contents

- Final report in Word format.
- `prototype/`: application, pinned PostgreSQL driver requirements, original demo video, public TLS CA, setup script, business/concurrency tests and browser test source.
- `sql/postgresql/`: schema, synthetic data, exact final data snapshot, guarded business routines, ten SELECT tasks, fixed report gateway and rollback verification SQL.
- `交付物/ER1.png` and `ER2.png`: the two views of one conceptual model.
- `数据字典_PostgreSQL.md`: field and physical-design details.
- `验证记录/`: actual returned rows, structural and business results, browser screenshots, a small EXPLAIN observation and a rollback-only fresh-schema reconstruction.
- `DEMO_5min.md`: timed demonstration and oral-defense guide.

## Run on the existing team computer

Run `prototype/start.command`, then open http://127.0.0.1:5413 . A public clone has no credentials. Configure your own project using the setup instructions below.

## Reproduce from this archive

This public edition omits student names and student IDs. Private credentials, virtual environments and browser sessions are deliberately excluded. Create a fresh free Supabase project and obtain its actual Direct connection host and administrator password. Follow `prototype/README.md`, install the pinned requirements into a local virtual environment, then run:

```sh
.venv/bin/python setup_demo.py --host '<actual project database host>'
```

The setup script generates five restricted demo logins and applies schema → exact final snapshot → business routines → report interface → trigger fix. It refuses existing business schemas or same-named roles rather than overwriting them. Database credentials never enter the browser source. The administrator password is prompted and not saved.

`02_seed.sql` is the original 69-row fixture. `02_final_snapshot.sql` restores the final report's 100-row capture. Choose exactly one data file; apply it after 01 and before the business triggers. Subsequent demonstrations legitimately change counts and generated IDs.

## Verified result and scope

31 structural probes, 21 real-login business/concurrency tests, four immutability probes and 14 browser checks passed. The browser tests cover actual database writes, rejected identity substitution, CSRF and a 390px layout. A separate rollback-only reconstruction created the complete ten-table snapshot and all five functions, then left no rehearsal schema behind.

The prototype uses five controlled database accounts. Open registration, account recovery, media upload/transcoding, recommendation and production deployment are out of scope. Media remains outside the relational tables. No production performance claim is made from the small EXPLAIN observation.

## Team submission

Only the group leader should upload one team copy, following the actual Canvas format and deadline. This package has not been uploaded on the team's behalf. Rehearse the five-minute demonstration and check that the free Supabase project is active before presenting.
