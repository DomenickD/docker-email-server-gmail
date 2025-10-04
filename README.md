# Docker Mailserver with Streamlit Email Sender

This project demonstrates how to wire together the
[docker‑mailserver](https://github.com/docker-mailserver/docker-mailserver)
image with a minimal Streamlit front‑end for sending
plain‑text emails.  It is intended for **testing and development
only**—it does *not* configure DNS records, TLS certificates or
spam/virus filtering, and will not deliver reliably on the
public internet without additional setup.  However it
provides a convenient local SMTP relay and a simple web
interface for exploring how email sending works in
Dockerised environments.

## Directory structure

```
docker_email_server/
├── docker-compose.yml          # Compose definition for mailserver and Streamlit
├── docker-data/                # Persisted volumes for mail, state, logs and config
└── streamlit_app/              # Source code for the Streamlit front‑end
    ├── Dockerfile              # Build instructions for the Streamlit image
    ├── app.py                  # Streamlit UI code
    ├── email_utils.py          # Helper functions to load config and send email
    └── requirements.txt        # Python dependencies
```

## Quick start

1. **Prerequisites:** Install Docker and Docker Compose (v2
   recommended).

2. **Clone this repository** and change into the project
   directory:

   ## Docker Mailserver + Streamlit — local, self‑contained email sender

   This repository provides a small Streamlit web UI that sends
   plain text email through a local SMTP relay implemented in this
   project. The relay stores every accepted message locally and
   can optionally forward mail via an authenticated outbound SMTP
   relay (for example Gmail with an App Password). The setup is
   intended for development and testing; it is not a production
   mail hosting configuration.

   Note: this project already supports sending via Gmail when you
   configure an App Password (see "Sending to Gmail" below for exact
   steps).

   See this repo for information on adapting this.
   https://github.com/docker-mailserver/docker-mailserver?tab=readme-ov-file

   ## What’s in this repo

   - `docker-compose.yml` — Compose definition for the local relay and
      the Streamlit app.
   - `smtp_relay/` — small Python service (aiosmtpd + FastAPI) that
      captures mail and can forward to an outbound relay or directly
      to recipient MX hosts.
   - `streamlit_app/` — Streamlit UI and helper utilities used to
      construct and submit messages.
   - `docker-data/` — host side volumes (mail store, logs, state).

   ## Quick start (local testing)

   Prerequisites:
   - Docker and Docker Compose (v2 recommended)

   1. Copy the example env file for the SMTP relay and populate it locally:

   ```powershell
   copy .env.relay.example .env.relay
   notepad .env.relay   # (or edit with your editor)
   ```

   2. Edit `.env.relay` and set values. For local capture only you can
       leave `SMTP_RELAY_SERVER` blank. To deliver to Gmail set the
       values as shown in the Google App Password section below.

      Tip: If you want to deliver to a Gmail address, this repository
      works with Gmail when you provide an App Password in `.env.relay`.

   3. Start the services (this builds images if needed):

   ```powershell
   docker compose --env-file .env.relay up --build -d
   ```

   4. Open the Streamlit UI at http://localhost:8501. Fill the form
       and click **Send Email**. The app will report success if the
       local relay accepted the message.

   5. Inspect stored messages (local copy):

   ```powershell
   curl http://localhost:8025/messages
   dir .\docker-data\mail-data
   ```

   6. To stop:

   ```powershell
   docker compose down
   ```

   ## Sending to Gmail: App Password instructions

   Google requires an application‑specific password (App Password) to
   authenticate SMTP clients when your account has 2‑step verification
   enabled. If you want the relay to forward mail to `deothe1@gmail.com`
   through Gmail (recommended, because direct-to-MX is often blocked by
   provider policies), create an App Password and put it into `.env.relay`.

   Create an App Password (if you use 2‑step verification):

   1. Go to https://myaccount.google.com/apppasswords
   2. Sign in and follow Google’s prompts.
   3. Select App = Mail and choose a device name (e.g. `docker-relay`).
   4. Copy the 16‑character password Google shows and paste it into
       `SMTP_RELAY_PASSWORD` in your local `.env.relay` (do not commit it).

   Example `.env.relay` for Gmail (DO NOT commit):

   ```text
   SMTP_RELAY_SERVER=smtp.gmail.com
   SMTP_RELAY_PORT=587
   SMTP_RELAY_USERNAME=youremail@gmail.com
   SMTP_RELAY_PASSWORD=PASTE_YOUR_APP_PASSWORD_HERE
   SMTP_RELAY_STARTTLS=1
   ```

   Then recreate the relay so it picks up the env file:

   ```powershell
   docker compose --env-file .env.relay up -d --force-recreate smtp_relay
   ```

   Tail logs while you send a test and look for either
   `Delivered message to ... via relay smtp.gmail.com` (success) or
   authentication errors (534/535) which indicate an App Password issue.

   ## How the relay works (short)

   - The relay stores every accepted message under `/app/mail_store`
      (host path `./docker-data/mail-data`). This ensures a local copy
      even if outbound delivery fails.
   - If `SMTP_RELAY_SERVER` is set, the relay attempts to use that
      SMTP server with STARTTLS and LOGIN (using `SMTP_RELAY_USERNAME`
      / `SMTP_RELAY_PASSWORD`) before falling back to direct MX
      delivery. Direct MX delivery to Gmail is commonly rejected with
      550 NotAuthorizedError unless sent from an authorized IP.

   ## Debugging & logs

   - Tail relay logs:

   ```powershell
   docker logs smtp_relay --follow
   ```

   - Tail Streamlit logs:

   ```powershell
   docker logs streamlit_app --follow
   ```

   - Inspect stored messages:

   ```powershell
   curl http://localhost:8025/messages
   ```

   Common log messages:
   - `534 Application-specific password required` — you must use a
      Google App Password, not the account password.
   - `550 NotAuthorizedError` — Gmail rejected direct-to-MX from your
      IP; use an authenticated relay instead.

   ## Security & publishing to GitHub

   - Never commit `.env.relay` or any file containing secrets. Add
      `.env.relay` to `.gitignore` and keep a safe `.env.relay.example` in
      the repo instead.
   - If you accidentally committed secrets, rotate them immediately and
      consider using tools like `git-filter-repo` or BFG to purge history
      before pushing to a public repository (the README includes a
      short guide on cleaning history).

   ## Files to create / update locally

   - `.env.relay` — local file with real credentials (do not commit)
   - `.env.relay.example` — commit this file with placeholders
   - `.gitignore` — ensure it ignores `./docker-data/` and `.env.relay`

   ## Next steps and improvements

   - Add authenticated delivery reporting to the Streamlit UI.
   - Add retries/backoff for outbound delivery attempts.
   - For production: set up proper DNS (SPF, DKIM) and use a trusted
      outbound relay service or cloud email provider.

   If you want, I can add a `README` section that includes the exact
   PowerShell commands to scrub secrets from git history and a sample
   GitHub Actions workflow that uses GitHub Secrets. Tell me which
   you prefer and I’ll add it.

submitted it calls `email_utils.send_email()` to
construct and send the message.  If the send succeeds a
success notification is displayed; otherwise an error
message appears.

## Important notes

* **Not production ready.**  This setup is designed for
  testing and learning.  For public deployments you need
  to configure proper DNS (MX, SPF, DKIM and DMARC) and
  obtain TLS certificates【993985963063397†L277-L297】.  Without these your mail may be
  rejected or marked as spam by other servers.

* **Security.**  Do not expose this mail server to the
  internet without enabling anti‑spam, anti‑virus and
  authentication restrictions.  See the docker‑mailserver
  documentation for recommended environment variables and
  examples.

* **Passwords.**  The example password `Passw0rd1!` is for
  demonstration only.  Choose a strong secret in your own
  environment and update both the compose file and the
  `setup` command accordingly.

* **Volume ownership on Windows.**  If you run this on
  Windows (especially WSL2) you may need to adjust volume
  permissions or use named volumes instead of bind mounts to
  avoid file access errors.  The current configuration uses
  bind mounts for clarity.

Enjoy exploring email sending with Docker!