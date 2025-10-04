"""Utility functions for sending email via SMTP.

This module exposes two helper functions:

* :func:`get_smtp_config` reads the SMTP server
  configuration from environment variables.  It ensures
  that all required values are present and that the
  `SMTP_PORT` variable can be converted to an integer.

* :func:`send_email` constructs and dispatches a plain
  text email using Python's :mod:`smtplib` library.  It
  supports both STARTTLS (usually port 587) and
  implicit SSL (port 465) connections.  Callers must
  supply the recipient address, subject and body along
  with the server details and credentials.  If no
  sender is provided the username will be used as the
  ``From`` address.

These functions are designed to be composable and
reusable from the Streamlit front-end or any other
Python code.  They raise exceptions on misconfigured
environment or network errors, allowing the caller to
provide meaningful feedback to the end user.

Note
----
In production you should consider using a more robust
mail library (e.g. ``email.message.EmailMessage``) and
handle errors more gracefully.  This example keeps
things simple for clarity.
"""

import os
import smtplib
from email.mime.text import MIMEText
from typing import Tuple, Optional

from dotenv import load_dotenv


def get_smtp_config() -> Tuple[str, int, Optional[str], Optional[str], str, bool]:
    """Load SMTP configuration from environment variables.

    The following variables must be defined in the process
    environment or a ``.env`` file in the working
    directory:

    - ``SMTP_SERVER`` - The hostname or IP address of the
      SMTP server to use.
    - ``SMTP_PORT`` - The port number (as an integer) on
      which the SMTP server listens.  Use 587 for TLS or
      465 for implicit SSL.
    - ``SMTP_USERNAME`` - The username for authenticating
      with the SMTP server.
    - ``SMTP_PASSWORD`` - The corresponding password.
    - ``SENDER_EMAIL`` - The email address to appear in
      the ``From`` header.  If you omit this the
      ``SMTP_USERNAME`` will be used instead.

    Returns
    -------
    tuple
        A five-tuple ``(server, port, username, password, sender)``
        with the loaded configuration values.

    Raises
    ------
    KeyError
        If any required environment variable is missing.
    ValueError
        If ``SMTP_PORT`` cannot be converted to an integer.
    """
    # Load variables from .env file if present.  This call
    # is idempotent and does nothing if the file is absent.
    load_dotenv()
    required_keys = ["SMTP_SERVER", "SMTP_PORT", "SENDER_EMAIL"]
    missing = [k for k in required_keys if not os.getenv(k)]
    if missing:
        raise KeyError(f"Missing required environment variables: {', '.join(missing)}")
    # Optional username/password for authenticated SMTP. If
    # SMTP_NO_AUTH is set (to a truthy value) the app will skip
    # AUTH and STARTTLS which is useful for a local relay on port 25.
    no_auth = os.getenv("SMTP_NO_AUTH") in ("1", "true", "True")
    port_str = os.getenv("SMTP_PORT")
    if not port_str:
        raise ValueError("SMTP_PORT must be provided")
    try:
        port = int(port_str)
    except Exception as exc:
        raise ValueError("SMTP_PORT must be an integer") from exc
    server = os.getenv("SMTP_SERVER")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SENDER_EMAIL") or username or ""
    return server, port, username, password, sender, no_auth


def send_email(
    recipient: str,
    subject: str,
    body: str,
    *,
    smtp_server: str,
    smtp_port: int,
    username: Optional[str],
    password: Optional[str],
    sender: Optional[str] = None,
    no_auth: bool = False,
) -> None:
    """Send a plain text email via SMTP.

    Parameters
    ----------
    recipient : str
        Destination email address.  Should be a valid
        RFC 2822 address.
    subject : str
        Message subject line.
    body : str
        Message body.  Newlines will be preserved.
    smtp_server : str
        Hostname or IP of the SMTP server.
    smtp_port : int
        Port number.  Use 587 for STARTTLS, 465 for
        implicit SSL.
    username : str
        Username for authentication.
    password : str
        Password for authentication.
    sender : Optional[str], default ``None``
        Address to use in the ``From`` header.  If not
        supplied, ``username`` is used.

    Raises
    ------
    smtplib.SMTPException
        If authentication or sending fails.
    """
    if sender is None:
        sender = username
    # Construct MIMEText message.  Using MIME classes
    # simplifies adding future headers such as CC/BCC.
    message = MIMEText(body, "plain", _charset="utf-8")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    # Choose SSL vs TLS based on port.  Port 465 uses
    # implicit SSL while other ports are upgraded via
    # STARTTLS.  Use a short timeout to avoid long hangs.
    timeout = 30
    # If the relay is configured to accept unauthenticated mail (e.g.
    # a local container on port 25) we send without STARTTLS / LOGIN.
    if no_auth or smtp_port == 25:
        with smtplib.SMTP(host=smtp_server, port=smtp_port, timeout=timeout) as server:
            server.sendmail(sender, [recipient], message.as_string())
        return

    if smtp_port == 465:
        with smtplib.SMTP_SSL(
            host=smtp_server, port=smtp_port, timeout=timeout
        ) as server:
            server.login(username, password)
            server.sendmail(sender, [recipient], message.as_string())
    else:
        with smtplib.SMTP(host=smtp_server, port=smtp_port, timeout=timeout) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.sendmail(sender, [recipient], message.as_string())
