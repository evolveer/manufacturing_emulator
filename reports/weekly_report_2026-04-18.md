# Manufacturing System Weekly Report

**Date Generated:** 2026-04-18 04:15:13

## System Health Status

| System | Status | Timestamp |
|---|---|---|
| MES | Online | 2026-04-18 04:15:13 |
| PCS | Online | 2026-04-18 04:15:13 |

## Manufacturing Execution System (MES) Summary

The MES is responsible for orchestrating production. Below is the summary of work orders and quality metrics for the week.

- **Total Machines Registered:** 15
- **Active Work Orders:** 7
- **Completed Work Orders:** 12
- **Total Quality Checks:** 154
- **Failed Quality Checks:** 8

### Quality Check Failures

| Work Order | Parameter | Value | Status |
|---|---|---|---|
| BAT-486B9F5B | api_weight_kg | 15.025 | fail |
| BAT-486B9F5B | excipient_weight_kg | 20.05 | fail |
| BAT-51C5F6CE | api_weight_kg | 15.025 | fail |
| BAT-51C5F6CE | excipient_weight_kg | 20.05 | fail |
| BAT-F1606035 | api_weight_kg | 15.025 | fail |
| BAT-F1606035 | excipient_weight_kg | 20.05 | fail |
| BAT-F9368E4E | api_weight_kg | 15.025 | fail |
| BAT-F9368E4E | excipient_weight_kg | 20.05 | fail |

## Process Control System (PCS) Summary

The PCS monitors real-time machine telemetry and manages equipment alarms.

- **Machines Currently Running:** 7 / 16
- **Active Alarms:** 3

### Active Equipment Alarms

| Machine ID | Alarm Code | Severity | Description | Time |
|---|---|---|---|---|
| 9 | TEMP_HIGH | warning | Temperature exceeds recommended range | 2026-04-17 19:32:09 |
| 1 | EJECTOR_JAM | error | Part ejector mechanism jammed | 2026-04-17 19:29:56 |
| 11 | MOLD_WEAR | info | Mold wear detected, maintenance recommended | 2026-04-17 19:27:41 |

## Potential Errors & Anomalies

- **ERROR:** Critical machine alarms are currently active and require immediate maintenance.
