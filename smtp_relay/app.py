"""Minimal SMTP receiver that accepts messages and exposes a tiny HTTP UI.

This uses aiosmtpd to run an SMTP server that stores received messages
on disk under /app/mail_store and exposes a small FastAPI endpoint to
list stored messages.  It's intended for local development and testing
so we don't rely on any external SMTP service.
"""

from __future__ import annotations

import asyncio
import email
import os
import logging
import smtplib
from typing import List

import dns.resolver

from aiosmtpd.controller import Controller
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn

MAIL_DIR = "/app/mail_store"
logging.basicConfig(level=logging.INFO)


class StoreHandler:
    async def handle_DATA(self, server, session, envelope):
        """Store message locally then attempt MX delivery for each RCPT TO.

        This function writes the raw message to disk (so there's always a
        local copy) and then tries to deliver the message to the recipient's
        MX servers (simple algorithm: try MX hosts in priority order). Any
        delivery failures are logged; failures do not remove the local copy.
        """
        os.makedirs(MAIL_DIR, exist_ok=True)
        i = 1
        while True:
            path = os.path.join(MAIL_DIR, f"msg-{i}.eml")
            if not os.path.exists(path):
                break
            i += 1
        # Write local copy
        try:
            with open(path, "wb") as fh:
                fh.write(envelope.content)
        except Exception:
            logging.exception("Failed to store message")
            return "451 Could not store message"

        # Attempt MX delivery for each recipient
        for rcpt in envelope.rcpt_tos:  # type: ignore[attr-defined]
            try:
                self._deliver_to_recipient(rcpt, envelope.content)
            except Exception:
                logging.exception("Delivery attempt failed for %s", rcpt)

        return "250 Message accepted for delivery"

    def _get_mx_hosts(self, domain: str) -> List[str]:
        """Return MX hostnames for domain ordered by priority."""
        answers = dns.resolver.resolve(domain, "MX")
        # MX records are tuples (priority, host)
        mx = sorted([(r.preference, str(r.exchange).rstrip(".")) for r in answers])
        return [host for _, host in mx]

    def _deliver_to_recipient(self, rcpt: str, content: bytes) -> None:
        """Resolve MX for the recipient domain and attempt SMTP delivery.

        This performs a simple connect/send sequence using smtplib.SMTP
        to the MX host on port 25. It does not implement retries or backoff.
        """
        # Prefer an authenticated outbound relay when configured. This
        # allows using smtp.gmail.com (with an app password) which will
        # typically accept delivery even when direct-to-MX is blocked.
        relay_host = os.getenv("SMTP_RELAY_SERVER")
        relay_port = (
            int(os.getenv("SMTP_RELAY_PORT")) if os.getenv("SMTP_RELAY_PORT") else 0
        )
        relay_user = os.getenv("SMTP_RELAY_USERNAME")
        relay_pass = os.getenv("SMTP_RELAY_PASSWORD")
        relay_starttls = os.getenv("SMTP_RELAY_STARTTLS", "1") in ("1", "true", "True")

        if relay_host:
            try:
                port = relay_port or 587
                logging.info(
                    "Using outbound relay %s:%s for %s", relay_host, port, rcpt
                )
                with smtplib.SMTP(relay_host, port, timeout=60) as s:
                    s.ehlo("local-relay")
                    if relay_starttls:
                        s.starttls()
                        s.ehlo()
                    if relay_user and relay_pass:
                        s.login(relay_user, relay_pass)
                    s.sendmail(envelope_from(content), [rcpt], content)
                logging.info("Delivered message to %s via relay %s", rcpt, relay_host)
                return
            except Exception as exc:
                logging.exception(
                    "Relay delivery to %s via %s failed", rcpt, relay_host
                )

        # Fallback to direct MX delivery
        domain = rcpt.split("@", 1)[1]
        mx_hosts = self._get_mx_hosts(domain)
        if not mx_hosts:
            raise RuntimeError(f"No MX hosts found for {domain}")

        last_exc = None
        for host in mx_hosts:
            try:
                logging.info(
                    "Attempting delivery of %s to %s (MX %s)", rcpt, domain, host
                )
                with smtplib.SMTP(host, 25, timeout=30) as s:
                    # Announce a reasonable EHLO name
                    s.ehlo("local-relay")
                    s.sendmail(envelope_from(content), [rcpt], content)
                logging.info("Delivered message to %s via %s", rcpt, host)
                return
            except Exception as exc:
                last_exc = exc
                logging.warning("Delivery to %s via %s failed: %s", rcpt, host, exc)
        # All MX attempts failed
        raise last_exc or RuntimeError("MX delivery failed")


def envelope_from(content: bytes) -> str:
    """Extract a sensible envelope-from address from the message headers.

    Falls back to 'postmaster@localhost' if no From header is present.
    """
    # If an authenticated outbound relay is configured, prefer its username
    # as the envelope-from (many relays require the MAIL FROM to match
    # the authenticated account or an approved alias).
    relay_user = os.getenv("SMTP_RELAY_USERNAME")
    if relay_user:
        return relay_user
    try:
        msg = email.message_from_bytes(content)
        frm = msg.get("From")
        if frm:
            # Attempt a naive extraction of email address
            if "@" in frm:
                return frm.split()[-1].strip("<>\n\r")
            return frm
    except Exception:
        pass
    return "postmaster@localhost"


app = FastAPI()


@app.get("/messages", response_class=PlainTextResponse)
def list_messages():
    if not os.path.isdir(MAIL_DIR):
        return "No messages"
    files = sorted(os.listdir(MAIL_DIR))
    out = []
    for fname in files:
        p = os.path.join(MAIL_DIR, fname)
        with open(p, "r", encoding="utf8") as fh:
            hdr = fh.read().splitlines()[:20]
        out.append(f"--- {fname} ---\n" + "\n".join(hdr))
    return "\n\n".join(out) or "No messages"


def start_smtp(loop):
    handler = StoreHandler()
    controller = Controller(handler, hostname="0.0.0.0", port=25)
    controller.start()
    return controller


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    controller = start_smtp(loop)
    try:
        uvicorn.run(app, host="0.0.0.0", port=8025)
    finally:
        controller.stop()
