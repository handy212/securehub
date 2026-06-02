# Guard mobile API quick reference

Base URL: `/api/v1/guarding/`

Authentication: JWT bearer token. User must have a linked `GuardProfile`.

Profile: `GET /api/v1/profile/` returns `account_kind: "guard"` and `guard_profile_id`.

## Shifts and attendance

| Method | Path | Description |
|--------|------|-------------|
| GET | `me/shifts/` | List shift assignments |
| POST | `me/shifts/<assignment_id>/accept/` | Accept assignment |
| POST | `me/shifts/<assignment_id>/decline/` | Decline assignment |
| POST | `me/shifts/<assignment_id>/clock/` | Clock in/out (`event_type`, GPS fields) |

## Patrols

| Method | Path | Description |
|--------|------|-------------|
| GET | `me/patrol-rounds/` | List patrol rounds for guard assignments |
| POST | `me/patrol-rounds/<round_id>/scan/` | Record checkpoint scan |
| POST | `me/patrol-rounds/<round_id>/complete/` | Complete patrol round |

Scan body may include `client_scan_id` (UUID) and `offline_created_at` for offline sync.

## Safety and dispatch

| Method | Path | Description |
|--------|------|-------------|
| POST | `me/location/` | Location ping (requires clocked-in assignment) |
| POST | `me/panic/` | Raise SOS |
| POST | `me/welfare-checks/<id>/confirm/` | Confirm welfare check |
| GET | `me/dispatch-tasks/` | Assigned dispatch tasks |
| POST | `me/dispatch-tasks/<id>/<action>/` | `accept`, `en-route`, `arrive`, `resolve` |

## Reports

| Method | Path | Description |
|--------|------|-------------|
| GET | `me/reports/` | List field reports |
| POST | `me/reports/` | Submit field report |
| GET | `me/welfare-checks/` | List pending welfare checks |
| POST | `me/welfare-checks/{id}/confirm/` | Confirm welfare check |
| GET | `me/post-orders/` | Post orders for assigned posts |
| GET | `me/report-templates/` | Report templates |

## Push deep links

FCM `data` payload includes `event_type`, `object_id`, and `route` when sent via guarding alerts.
