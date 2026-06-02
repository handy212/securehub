# Alarm Hub Integration Plan

This workspace currently contains the Hik-Partner Pro API guide and a proposed plan for building an `Alarm Hub` platform on top of it.

## Workspace Status

The workspace now includes:

- [backend](/home/dev/SecureHub/backend) with a Django + Django REST Framework API and staff console
- [securehub_mobile](/home/dev/SecureHub/securehub_mobile) with the Flutter mobile app
- [backend/README.md](/home/dev/SecureHub/backend/README.md) with backend setup notes
- [securehub_mobile/README.md](/home/dev/SecureHub/securehub_mobile/README.md) with mobile integration notes

## Documentation

Product and user guides (features, personas, workflows) live in **[docs/README.md](/home/dev/SecureHub/docs/README.md)**:

- [System overview](/home/dev/SecureHub/docs/system-overview.md) — mental model and how modules connect
- [Feature guide](/home/dev/SecureHub/docs/feature-guide.md) — capability catalog by module
- [Staff console user guide](/home/dev/SecureHub/docs/user-guide-staff-console.md)
- [Guarding operations](/home/dev/SecureHub/docs/user-guide-guarding-ops.md)
- [Field guard (mobile)](/home/dev/SecureHub/docs/user-guide-guard-mobile.md)
- [Alarm customer (mobile)](/home/dev/SecureHub/docs/user-guide-alarm-customer.md)
- [Guarding client portal](/home/dev/SecureHub/docs/user-guide-guarding-client.md)

In the running app, staff can read the same guides under **Help** in the console sidebar (`/console/help/`).

Technical references: [operator RBAC](/home/dev/SecureHub/docs/operator-rbac.md), [guard mobile API](/home/dev/SecureHub/docs/guard-mobile-api.md), [emergency runbook](/home/dev/SecureHub/docs/emergency-addon-runbook.md).

## Product Goal

Build an alarm management platform for intruder alarm systems where:

- installers or operators can register sites and devices
- customers can be assigned to one or more sites
- customers can arm, disarm, stay arm, and clear/cancel alarms
- customers receive real-time alerts and notifications
- a mobile app can later use the same backend APIs

## Hik-Partner Pro APIs Found In The PDF

From the PDF bookmarks in [Hik-Partner Pro OpenAPI Developer Guide_V2.14.0_20251021.pdf](/home/dev/SecureHub/Hik-Partner%20Pro%20OpenAPI%20Developer%20Guide_V2.14.0_20251021.pdf), the relevant API areas are:

- `POST /api/hpcgw/v1/token/get`
- Site management:
  - `POST /api/hpcgw/v1/site/add`
  - `POST /api/hpcgw/v1/site/search`
  - `POST /api/hpcgw/v1/site/share`
  - `POST /api/hpcgw/v2/site/assign`
  - `POST /api/hpcgw/v2/site/customer/list`
  - `POST /api/hpcgw/v1/site/customer/detail`
  - `POST /api/hpcgw/v1/site/customer/account/update`
  - `POST /api/hpcgw/v1/site/customer/devices/update`
- Device management:
  - `POST /api/hpcgw/v2/device/add`
  - `POST /api/hpcgw/v1/device/list`
  - `GET/PUT/POST/DELETE /api/hpcgw/v1/device/transparent/{isapi uri}`
- Events and alarms:
  - `POST /api/hpcgw/v1/mq/subscribe`
  - `POST /api/hpcgw/v1/mq/messages`
  - `POST /api/hpcgw/v1/mq/offset`
  - `POST /api/hpcgw/v1/alarm/pictureurl`
  - webhook config endpoints under `/api/hpcgw/webhook/v1/config/*`
- Intruder alarm ISAPI endpoints exposed through transparent device access:
  - `/ISAPI/SecurityCP/control/arm/<ID>?ways=<string>&format=json`
  - `/ISAPI/SecurityCP/control/disarm/<ID>?format=json`
  - `/ISAPI/SecurityCP/control/clearAlarm/<ID>?format=json`
  - `/ISAPI/SecurityCP/status/subSystems?format=json`
  - `/ISAPI/SecurityCP/status/zones?format=json`

## Recommended Architecture

Use a backend-first design so both web and mobile clients use the same service.

### Core services

1. `partner-adapter`
   Talks to Hik-Partner Pro.
   Handles token management, request signing if required, retries, rate limits, and transparent ISAPI calls.

2. `alarm-hub-api`
   Your own business API.
   Manages customers, sites, permissions, mobile sessions, notification rules, and audit logs.

3. `event-processor`
   Receives MQ or webhook events from Hik-Partner Pro.
   Normalizes alarm/device events into your internal event format and triggers notifications.

4. `notification-service`
   Sends push notifications, SMS, email, or in-app alerts.

5. `mobile app`
   Uses your backend only.
   It should never call Hik-Partner Pro directly.

## Suggested Data Model

### Main entities

- `Customer`
- `Site`
- `CustomerSiteAccess`
- `AlarmPanelDevice`
- `Subsystem`
- `Zone`
- `AlarmEvent`
- `ArmDisarmCommand`
- `NotificationDelivery`
- `UserSession`

### Important relationships

- one customer can access many sites
- one site can have many devices
- one alarm panel can have many subsystems
- one subsystem can have many zones
- alarm events belong to a site and optionally a subsystem or zone

## Feature Mapping

### 1. Site onboarding

- create or discover the site in Hik-Partner Pro
- assign the site to the customer
- link alarm devices to the site
- store your own internal site record and access rules

### 2. Customer assignment

Use the handover and customer APIs to:

- hand over a site to the end user with `POST /api/hpcgw/v2/site/handover/share`
- fetch customers for a site with `POST /api/hpcgw/v2/site/customer/list`
- inspect customer permissions with `POST /api/hpcgw/v1/site/customer/detail`
- update customer account details with `POST /api/hpcgw/v1/site/customer/account/update`
- control which devices and AX Pro permissions the customer can operate with `POST /api/hpcgw/v1/site/customer/devices/update`

Important correction from the PDF:
`POST /api/hpcgw/v2/site/assign` is for assigning site manager employees, not for assigning end customers.

### 3. Arm / disarm / stay arm / cancel alarm

Use the transparent device API with the alarm ISAPI paths:

- arm: `/ISAPI/SecurityCP/control/arm/<partitionNo>?ways=<mode>&format=json`
- disarm: `/ISAPI/SecurityCP/control/disarm/<partitionNo>?format=json`
- cancel or clear alarm: `/ISAPI/SecurityCP/control/clearAlarm/<partitionNo>?format=json`

Assumption:
The PDF confirms `ways=stay` for stay arming and `ways=away` for away arming.
The PDF also confirms the `<ID>` in the URI is the partition number, not an arbitrary subsystem identifier.

### 4. Live status

Poll or refresh:

- `/ISAPI/SecurityCP/status/subSystems?format=json`
- `/ISAPI/SecurityCP/status/zones?format=json`

Use this to show:

- armed or disarmed state
- subsystem health
- zone open or closed state
- active alarms and uncleared alarms

### 5. Real-time alerts

Prefer event push over polling:

- configure MQ subscription with `POST /api/hpcgw/v1/mq/subscribe`
- either poll events with `POST /api/hpcgw/v1/mq/messages`, or
- configure webhook push with `/api/hpcgw/webhook/v1/config/*`

Then normalize events into app-friendly types such as:

- `alarm_triggered`
- `alarm_cleared`
- `device_offline`
- `device_online`
- `zone_open`
- `zone_restored`
- `arm_success`
- `disarm_success`
- `command_failed`

## Security Model

- keep Hik credentials and tokens only on the backend
- issue your own JWT or session tokens to web and mobile clients
- enforce per-customer authorization at the site level
- require audit logging for every arm, disarm, and clear alarm action
- add command idempotency keys to avoid duplicate control actions
- record the operator, customer, site, subsystem, request payload, response, and timestamp

## MVP Scope

Build these first:

1. authenticate with Hik-Partner Pro
2. list sites
3. assign customer to site
4. list devices for a site
5. get subsystem and zone status
6. arm, disarm, stay arm, clear alarm
7. ingest alarm events
8. push notifications to customer devices

## Recommended Tech Stack

If you want a practical stack for fast delivery:

- backend: `Django` with `Django REST Framework`
- database: `PostgreSQL`
- queue: `Redis` or `RabbitMQ`
- mobile app later: `Flutter`
- push notifications: `Firebase Cloud Messaging`

## Delivery Phases

### Phase 1

- implement Hik token flow
- add site and device sync
- build transparent ISAPI wrapper

### Phase 2

- implement customer-site assignment
- implement arm, disarm, stay arm, and clear alarm APIs
- add command audit trail

### Phase 3

- implement webhook or MQ event ingestion
- add notification rules and mobile push
- add event timeline per site

### Phase 4

- build customer mobile app
- add multi-site dashboards
- add installer and admin roles

## Open Items To Confirm From The PDF

- the exact request and response bodies for:
- token retrieval
- the exact response wrapper for token retrieval because the document shows inconsistent examples between the typical application section and the API reference
- the event payload schema for intrusion alarms and zone state changes
- whether to use long polling or webhook delivery in production

## PDF Review Notes

Important findings from the PDF body:

- after token retrieval, follow-up API calls should use the returned `areaDomain`
- `Authorization` is `Bearer <accessToken>`
- transparent ISAPI calls require `X-Devserial`
- AX Pro transparent control may also require `X-Username`, `X-Password`, and `X-Userlevel`
- webhook configuration requires HTTPS and signature verification
- webhook delivery does not replace subscription: you still subscribe with `POST /api/hpcgw/v1/mq/subscribe`

## Best Next Step

Start with a backend service that exposes your own REST API:

- `POST /auth/login`
- `GET /sites`
- `GET /sites/:siteId/status`
- `POST /sites/:siteId/subsystems/:id/arm`
- `POST /sites/:siteId/subsystems/:id/disarm`
- `POST /sites/:siteId/subsystems/:id/stay-arm`
- `POST /sites/:siteId/subsystems/:id/clear-alarm`
- `GET /sites/:siteId/events`

Then connect those endpoints to Hik-Partner Pro through a dedicated adapter layer.

For this stack, the recommended starting structure is:

- Django project for the API and admin
- Django REST Framework for customer and mobile endpoints
- a dedicated Hik-Partner Pro integration app for token, site, device, and command flows
- Celery workers for event ingestion, retries, and notifications
- Flutter app consuming only your Django API

## Current Scaffold

### Backend

- Django project config under [backend/config](/home/dev/SecureHub/backend/config)
- domain apps under [backend/apps](/home/dev/SecureHub/backend/apps)
- JWT auth routes, site listing, site status, site events, and subsystem command endpoints
- Hik adapter service stub ready to be connected to the real transparent device API

### Mobile

- Flutter app entrypoint in [mobile/lib/main.dart](/home/dev/SecureHub/mobile/lib/main.dart)
- login screen, site list screen, and site detail screen with alarm action buttons
- mock repository that can be replaced with real API calls to the Django backend

## Setup Notes

### Backend

1. Create a Python virtual environment in [backend](/home/dev/SecureHub/backend).
2. Install [backend/requirements.txt](/home/dev/SecureHub/backend/requirements.txt).
3. Copy [backend/.env.example](/home/dev/SecureHub/backend/.env.example) to `.env`.
4. Run `python manage.py makemigrations` and `python manage.py migrate`.
5. Start the API with `python manage.py runserver`.

### Mobile

1. Run `flutter pub get` in [mobile](/home/dev/SecureHub/mobile).
2. Replace the mock repository with a real Django API client.
3. Add JWT token storage and notification registration.
