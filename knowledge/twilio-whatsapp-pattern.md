# Twilio WhatsApp API — n8n HTTP Request Pattern

## Receiving Messages
Twilio POSTs to n8n webhook. Form-encoded body:
- Body = message text
- From = whatsapp:+1XXXXXXXXXX
- To = bot's number
- MessageSid = unique ID

## Sending Messages
POST https://api.twilio.com/2010-04-01/Accounts/[ACCOUNT_SID]/Messages.json
- Auth: Basic (username: ACCOUNT_SID, password: AUTH_TOKEN)
- Content-Type: application/x-www-form-urlencoded
- Form body:
  - To: whatsapp:+1XXXXXXXXXX
  - From: whatsapp:+1XXXXXXXXXX (bot number)
  - Body: [message text]

## Notes
- 24-hour session window resets when user messages — no template approval needed for replies
- Employees initiate conversations in a dedicated group
