"""Streamlit front-end for sending email via docker-mailserver.

This application provides a simple web interface for sending
plain text emails through a locally hosted SMTP relay.  It
relies on environment variables for configuration (see the
accompanying ``Dockerfile`` and ``docker-compose.yml`` for
details) and uses helper functions from :mod:`email_utils` to
construct and dispatch messages.

Running this script outside of Docker is also supported as
long as the necessary environment variables are defined.
"""

from __future__ import annotations

import os
import streamlit as st

from email_utils import get_smtp_config, send_email


def main() -> None:
    """Render the Streamlit UI and handle form submission."""
    st.set_page_config(page_title="Mailserver Email Sender", page_icon="📧")
    st.title("📧 Send an Email via Local Mailserver")
    st.write(
        "This Streamlit app allows you to send a plain text email via "
        "the local docker-mailserver. Configure the SMTP credentials in "
        "your environment and provide the recipient, subject and message "
        "below. When you click *Send Email*, the message will be sent "
        "through the running mail server."
    )

    default_recipient = os.getenv("DEFAULT_RECIPIENT", "")
    with st.form(key="email_form"):
        recipient = st.text_input(
            "Recipient Email", value=default_recipient, placeholder="user@example.com"
        )
        subject = st.text_input("Subject", value="", placeholder="Subject line")
        body = st.text_area("Message", value="", height=200)
        submit = st.form_submit_button("Send Email")

    # Small convenience: preview messages stored by the local relay
    if st.button("Preview stored messages"):
        try:
            import requests

            resp = requests.get("http://smtp_relay:8025/messages", timeout=5)
            st.text(resp.text)
        except Exception as exc:
            st.error(f"Could not fetch stored messages: {exc}")

    if submit:
        if not recipient or not subject or not body:
            st.error("All fields are required to send an email.")
            return
        try:
            smtp_server, smtp_port, username, password, sender, no_auth = (
                get_smtp_config()
            )
        except (KeyError, ValueError) as exc:
            st.error(f"Configuration error: {exc}")
            return
        try:
            send_email(
                recipient=recipient.strip(),
                subject=subject.strip(),
                body=body,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                username=username,
                password=password,
                sender=sender,
                no_auth=no_auth,
            )
        except Exception as exc:
            st.error(f"Failed to send email: {exc}")
        else:
            st.success(f"Email successfully sent to {recipient}!")


if __name__ == "__main__":
    main()
