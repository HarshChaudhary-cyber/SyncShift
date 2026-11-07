# Manual university testing

Use the current [local demo guide](demo-testing.md) for migration, seed, reset, credentials, API verification and startup commands. The former Apex/Beacon credentials and broad domain-based reset instructions have been retired.

The current local dataset contains SSDEMO and RIVERDEMO. Admin, professor and student browser paths were verified against the isolated demo backend. For repeatable API scenarios, run `backend/verify_syncshift_demo_api.py` from `backend`; it clones the demo database before writing any test changes.
