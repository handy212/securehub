# Guard Monitoring System Roadmap

## Goal

Expand SecureHub from an alarm and emergency response platform into a full guard monitoring and workforce management system. The target is an end-to-end platform that manages guards from recruitment through active field operations, client reporting, payroll/billing, compliance, and offboarding.

## Current SecureHub Baseline

SecureHub already has a strong security operations foundation:

- Customer, site, subscription, and payment management.
- Hikvision site/device integration.
- Alarm panels, subsystems, zones, peripherals, and outputs.
- Alarm event ingestion, acknowledgement, and command audit history.
- Emergency request workflow with assignment, dispatch, arrival, resolution, and cancellation states.
- Firebase push device registration.
- Flutter mobile app foundation for customer alarm, site, device, emergency, message, and profile flows.
- Admin dashboard foundation for sites, customers, subscriptions, emergency services, broadcasts, and site consoles.

The missing layer is guard workforce management: recruitment, guard HR records, scheduling, patrols, checkpoint verification, field reports, supervisor workflows, client reporting, and back-office financial operations.

## Market Reference

Current guard management platforms such as TrackTik, Trackforce/GuardTek, QR-Patrol, Belfry, OfficerReports, PatrolTech, GuardTrac, and similar products commonly include:

- Applicant tracking and guard onboarding.
- Guard profiles, documents, licenses, certifications, and training.
- Shift scheduling, timekeeping, overtime control, and attendance.
- QR/NFC/GPS checkpoint patrols.
- GPS location tracking and geofencing.
- Incident reports, daily activity reports, maintenance reports, and visitor logs.
- Mobile guard app with offline support.
- SOS/panic button and lone worker welfare checks.
- Command center with live guard map, dispatch, and alerts.
- Client portal with reports, patrol proof, and activity history.
- Payroll, billing, contract rates, and profitability reporting.
- Audit trails, compliance alerts, and role-based access.
- Integrations and APIs for HR, payroll, access control, video, and BI systems.

Reference sources:

- TrackTik: https://www.tracktik.com/
- Trackforce/GuardTek: https://www.trackforce.com/home/
- QR-Patrol: https://www.qrpatrol.com/features
- Belfry: https://www.belfrysoftware.com/
- OfficerReports: https://officerreports.com/
- PatrolTech: https://patroltech.online/en

## Product Pillars

### 1. Guard Lifecycle Management

Manage guards from application to offboarding.

Core features:

- Applicant profiles.
- Recruitment stages: applied, screened, interviewed, background check, hired, rejected.
- Interview notes and reviewer decisions.
- Background check status.
- Guard employee profile after hiring.
- Employment status: applicant, active, suspended, inactive, terminated.
- License and certification tracking.
- Training records.
- Document storage metadata for ID, contracts, permits, medicals, references, and certificates.
- Expiry alerts for licenses, documents, and certifications.
- Uniform and equipment assignment.
- Disciplinary notes and performance history.
- Offboarding checklist.

### 2. Site, Post, And Contract Setup

Extend existing SecureHub sites into guardable service locations.

Core features:

- Guard posts linked to existing `Site` records.
- Post instructions and post orders.
- Client contacts and escalation contacts.
- Guard service contract records.
- Bill rates, pay rates, overtime rules, and service-level expectations.
- Required qualifications per post.
- Required patrol routes per post.
- Site geofence boundary.
- Supervisor assignment per site/post.

### 3. Scheduling And Attendance

Plan coverage and verify attendance.

Core features:

- Shift templates.
- Recurring schedules.
- Open shifts.
- Guard availability.
- Leave/unavailability requests.
- Shift assignment.
- Shift swap requests.
- Conflict detection.
- Qualification matching.
- GPS/geofence clock-in and clock-out.
- Late clock-in alerts.
- No-show alerts.
- Early clock-out alerts.
- Break tracking.
- Overtime tracking.
- Timesheet approval.

### 4. Patrol And Checkpoint Monitoring

Prove guards performed required patrols.

Core features:

- Checkpoints per site/post.
- QR checkpoint support.
- NFC checkpoint support later.
- GPS-only virtual checkpoint support.
- Patrol route templates.
- Scheduled patrol rounds.
- Ad-hoc patrol rounds.
- Expected checkpoint sequence.
- Checkpoint scan timestamp.
- GPS validation at scan.
- Anti-fraud geofence radius.
- Missed checkpoint alerts.
- Late patrol alerts.
- Patrol completion status.
- Patrol history and proof report.
- Offline scan queue with later sync.

### 5. Field Reporting

Replace paper logs and informal messaging with structured records.

Core features:

- Daily Activity Reports.
- Incident Reports.
- Maintenance Reports.
- Visitor Logs.
- Parking/Violation Reports.
- Pass-on Logs.
- Custom form templates.
- Photos, videos, audio, and notes.
- GPS and timestamp metadata.
- Guard signature.
- Witness/client signature.
- Supervisor review and approval.
- Report correction workflow.
- Client-visible and internal-only visibility controls.

### 6. Guard Mobile App

Give guards a simple command center in the field.

Core features:

- Guard login.
- Today’s assigned shifts.
- Clock in/out.
- Active post view.
- Post orders.
- Patrol route and checkpoint scan.
- Incident/DAR form submission.
- Media upload.
- Push notifications.
- SOS/panic button.
- Welfare check timer.
- Supervisor chat or broadcast messages.
- Offline mode for reports and checkpoint scans.

### 7. Command Center

Give supervisors and operators live operational control.

Core features:

- Live map of active guards.
- Active shifts dashboard.
- Late/no-show/missed patrol queue.
- Open incidents queue.
- SOS and welfare alerts.
- Dispatch workflow.
- Assign nearest available guard.
- Link guard dispatch to alarm and emergency events.
- Escalation rules by site/client.
- Activity feed across all sites.
- Supervisor notes and handover.

### 8. Client Portal

Give clients controlled visibility without admin access.

Core features:

- Client login.
- Sites under contract.
- Live or near-real-time activity summary.
- Patrol completion reports.
- Incident reports.
- Daily activity reports.
- Attendance summary.
- Downloadable PDF/Excel reports.
- SLA/coverage proof.
- Invoice and payment history later.
- Client comments or report acknowledgement.

### 9. Payroll, Billing, And Profitability

Connect field activity to business operations.

Core features:

- Approved timesheets.
- Pay rates per guard/post/contract.
- Bill rates per client/site/post.
- Overtime rules.
- Allowances and deductions.
- Payroll export.
- Invoice generation.
- Invoice adjustments.
- Unbilled overtime tracking.
- Profitability by client/site/post.
- Payment tracking.

### 10. Compliance, Audit, And Security

Reduce liability and preserve evidence.

Core features:

- Role-based permissions for admins, supervisors, guards, clients, and customers.
- Immutable audit trail for critical actions.
- Document expiry alerts.
- License expiry alerts.
- Training renewal alerts.
- Supervisor approval audit.
- Location history retention policy.
- Report evidence retention policy.
- Data export controls.
- API access tokens for integrations.
- Privacy controls for guard location tracking.

## Proposed Backend Modules

Add a new Django app, likely named `guarding` or `workforce`.

Suggested model groups:

- `GuardApplicant`
- `RecruitmentStage`
- `GuardProfile`
- `GuardDocument`
- `GuardLicense`
- `GuardCertification`
- `GuardTrainingRecord`
- `GuardEquipmentIssue`
- `GuardPost`
- `PostOrder`
- `GuardContract`
- `Shift`
- `ShiftAssignment`
- `Availability`
- `LeaveRequest`
- `ClockEvent`
- `Timesheet`
- `Checkpoint`
- `PatrolRoute`
- `PatrolRound`
- `CheckpointScan`
- `GuardLocationPing`
- `FieldReport`
- `ReportTemplate`
- `ReportAttachment`
- `WelfareCheck`
- `GuardPanicAlert`
- `DispatchTask`
- `ClientPortalAccess`

## Recommended Delivery Phases

### Phase 1: Guard Registry And Basic Scheduling

Build the minimum guard operations backbone.

Deliverables:

- Guard profiles.
- Applicant-to-guard conversion.
- Guard document/license/certification records.
- Guard posts linked to existing sites.
- Shift creation and assignment.
- Basic mobile guard shift list.
- Clock in/out with GPS.
- Admin dashboard views for guards, posts, and shifts.

Success criteria:

- Admin can create a guard.
- Admin can assign a guard to a site/post shift.
- Guard can see assigned shift on mobile.
- Guard can clock in/out.
- Supervisor can see attendance and lateness.

### Phase 2: Patrol Routes And Checkpoints

Add core guard monitoring.

Deliverables:

- Checkpoints.
- QR code generation.
- Patrol routes.
- Scheduled patrol rounds.
- Mobile checkpoint scanning.
- GPS validation.
- Missed checkpoint alerts.
- Patrol completion report.

Success criteria:

- Supervisor can create a patrol route for a site.
- Guard can scan checkpoints during a shift.
- System can detect missed or late patrols.
- Client/supervisor can view patrol proof.

### Phase 3: Field Reports And Incident Workflow

Digitize field documentation.

Deliverables:

- Daily Activity Reports.
- Incident Reports.
- Maintenance Reports.
- Visitor Logs.
- Attachments.
- Supervisor review/approval.
- Client visibility rules.
- PDF/export-ready report views.

Success criteria:

- Guard can submit reports from mobile.
- Supervisor can review and approve reports.
- Client can view approved reports.
- Reports include timestamp, guard, site, GPS, and media evidence.

### Phase 4: Command Center And Emergency Linkage

Connect guard operations to SecureHub’s existing emergency and alarm foundation.

Deliverables:

- Live active guards dashboard.
- Guard location pings.
- SOS/panic alerts.
- Welfare checks.
- Dispatch tasks.
- Link dispatch tasks to `AlarmEvent` and `EmergencyRequest`.
- Supervisor escalation workflow.

Success criteria:

- Operator can see active guards on a map.
- Operator can dispatch a guard to an alarm or emergency request.
- Guard can accept, arrive, and resolve dispatch task.
- SOS creates an urgent command center alert.

### Phase 5: Client Portal, Payroll, Billing, And Analytics

Turn operations data into client value and business value.

Deliverables:

- Client guard-service portal.
- Patrol and activity summaries.
- Timesheet approval.
- Payroll export.
- Contract bill rates.
- Invoice generation.
- Profitability reports.
- Operational KPIs.

Success criteria:

- Client can see activity and reports for their sites.
- Finance can produce invoices from approved shifts.
- Management can see coverage, lateness, missed patrols, incident trends, and site profitability.

## MVP Scope

The first practical MVP should focus on:

- Guard profiles.
- Guard posts.
- Shift scheduling.
- GPS clock in/out.
- QR checkpoints.
- Patrol routes.
- Checkpoint scans.
- Missed patrol alerts.
- Basic incident and daily activity reports.
- Supervisor dashboard.
- Guard mobile workflow.

This MVP would make SecureHub usable as a real guard monitoring system before adding recruitment depth, payroll, client portal, and advanced analytics.

## Data And Integration Considerations

- Reuse existing `Site` records instead of creating a separate location model.
- Reuse existing users for guards where possible, with role/profile extensions.
- Reuse Firebase push notification infrastructure for guard alerts.
- Reuse emergency dispatch concepts where possible for guard dispatch tasks.
- Keep guard location tracking limited to active shifts unless explicitly configured otherwise.
- Preserve offline-first design for checkpoint scans and field reports.
- Use audit logs for all shift edits, patrol edits, report approvals, dispatch actions, and payroll-impacting changes.

## Open Product Decisions

- Should guards be normal Django users, or should guard identity be separated from customer/operator identity?
- Should the platform support third-party guard companies as tenants?
- Is the first target market internal SecureHub response teams, external private security companies, or both?
- Should QR-only patrols ship first, with NFC added later?
- Should payroll be built natively or exported to accounting/payroll tools first?
- How much client visibility should be available in the first release?
- What local compliance requirements apply for guard licensing, background checks, and employment records?

