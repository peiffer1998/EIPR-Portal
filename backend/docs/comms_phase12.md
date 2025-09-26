# Phase 12 – Communications Usage & Smoke Guide

## Email Templates & Outbound Messages
- Create a template:
  ```bash
  curl -X POST http://localhost:8000/api/v1/comms/emails/templates \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{"name":"welcome","subject_template":"Welcome {{ owner.first_name }}","html_template":"<p>Hello {{ owner.first_name }}</p>"}'
  ```
- Send the template to yourself (Mailhog at http://localhost:8025 will capture it):
  ```bash
  curl -X POST http://localhost:8000/api/v1/comms/emails/send \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{"owner_id":"<OWNER_UUID>","template_name":"welcome"}'
  ```

## Two-way SMS (DEV_SMS_ECHO mode)
- Ensure `.env` has `DEV_SMS_ECHO=true` and restart the API.
- Send an outbound SMS:
  ```bash
  curl -X POST http://localhost:8000/api/v1/comms/sms/send \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{"owner_id":"<OWNER_UUID>","body":"Test message"}'
  ```
- Simulate an inbound webhook (no signature check in dev):
  ```bash
  curl -X POST http://localhost:8000/api/v1/comms/sms/webhook \
       -H "Content-Type: application/x-www-form-urlencoded" \
       -d 'From=+15555550123&Body=Hello from owner'
  ```
- Staff notifications: fetch unread items after inbound webhook
  ```bash
  curl -X GET "http://localhost:8000/api/v1/comms/notifications?unread_only=true" \
       -H "Authorization: Bearer <TOKEN>"
  ```

## Campaign Preview & Send
- Preview recipients with an upcoming reservation:
  ```bash
  curl -X POST http://localhost:8000/api/v1/comms/campaigns/preview \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{"channel":"email","segment":{"has_upcoming_reservation":true}}'
  ```
- Send immediately using the template created earlier:
  ```bash
  curl -X POST http://localhost:8000/api/v1/comms/campaigns/send-now \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{"channel":"email","template_name":"welcome","segment":{"has_upcoming_reservation":true}}'
  ```

## Smoke Checklist
1. `PYTHONPATH=. .venv/bin/python -m pytest -q`
2. Start API with local env (SQLite or Postgres) so `Mailhog` captures outbound email.
3. Confirm outbound email appears in Mailhog and SMS echo writes to the database.
4. Run the inbound SMS webhook curl; verify staff notifications show the new message.
5. Run the campaign preview/send commands and confirm `campaign_sends` records are created.
