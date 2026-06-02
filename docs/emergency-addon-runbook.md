# Emergency Add-on Runbook

## Production Configuration

Set these environment variables before enabling the module in production:

```bash
SECUREHUB_EMERGENCY_SMS_RECIPIENTS="+233XXXXXXXXX,+233YYYYYYYYY"
SECUREHUB_EMERGENCY_SMS_PROVIDER="hubtel"
SECUREHUB_EMERGENCY_SMS_WEBHOOK_URL=""
HUBTEL_CLIENT_ID="..."
HUBTEL_CLIENT_SECRET="..."
HUBTEL_SENDER_NAME="SecureHub"
DEFAULT_FROM_EMAIL="alerts@your-domain.example"
```

Use `SECUREHUB_EMERGENCY_SMS_PROVIDER=webhook` only when a custom SMS relay is deployed, and set `SECUREHUB_EMERGENCY_SMS_WEBHOOK_URL` to that relay endpoint.

## Deploy Steps

```bash
cd backend
python manage.py migrate
python manage.py check
python manage.py test apps.emergency
```

Restart the Django web process and the Celery worker after migration so the API, console, and emergency notification task all load the new code.

## Smoke Test

1. Enable an emergency add-on for a test customer from `/console/subscriptions/` or `/console/emergency/services/`.
2. Sign in as that customer on mobile.
3. Send a site emergency request from the site home screen.
4. Confirm the request appears on `/console/emergency/`.
5. Assign it to an operator/patrol user.
6. Open `/console/map/` and confirm the red emergency marker is visible.
7. Cancel or resolve the request and confirm live location updates stop.

## Operator Flow

Use `/console/emergency/` as the incident queue:

- `Assign` chooses the operator/patrol owner and automatically acknowledges an open request.
- `Dispatch` marks patrol as sent.
- `Arrive` records arrival at the customer's location.
- `Resolve` closes a completed response.
- `Cancel` closes a false alarm or user-cancelled request.

Incident records are not hard-deleted from the dispatch queue; they remain available for audit and reporting.
