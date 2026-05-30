#!/usr/bin/env python3
"""Local dev SMTP interceptor - prints received emails to stdout instead of delivering them.

Run with:
    uv run python scripts/smtp-interceptor.py [host] [port]

Defaults: localhost:1025
"""
import asyncio
import io
import re
import sys
from datetime import datetime

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP, Envelope, Session

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"


class PrintingHandler:
    async def handle_RCPT(self, server: SMTP, session: Session, envelope: Envelope, address: str, rcpt_options: list) -> str:
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server: SMTP, session: Session, envelope: Envelope) -> str:
        content = envelope.content.decode("utf-8", errors="replace") if isinstance(envelope.content, bytes) else envelope.content
        timestamp = datetime.now().strftime("%H:%M:%S")

        sep = "-" * 60
        print(f"\n{BOLD}{CYAN}{sep}{RESET}")
        print(f"{BOLD}[EMAIL INTERCEPTED]  [{timestamp}]{RESET}")
        print(f"{CYAN}{sep}{RESET}")
        print(f"  {BOLD}From:{RESET}    {envelope.mail_from}")
        print(f"  {BOLD}To:{RESET}      {', '.join(envelope.rcpt_tos)}")

        subject_match = re.search(r"^Subject:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if subject_match:
            print(f"  {BOLD}Subject:{RESET} {subject_match.group(1).strip()}")

        seen: set[str] = set()
        links = [url for url in re.findall(r"https?://[^\s\"'<>]+", content) if not (url in seen or seen.add(url))]
        if links:
            print(f"\n{BOLD}{GREEN}  >> Links:{RESET}")
            for link in links:
                print(f"     {YELLOW}{link}{RESET}")

        print(f"{CYAN}{sep}{RESET}\n")
        sys.stdout.flush()
        return "250 Message accepted for delivery"


def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 1025

    handler = PrintingHandler()
    controller = Controller(handler, hostname=host, port=port)
    controller.start()

    print(f"{BOLD}{MAGENTA}SMTP interceptor listening on {host}:{port}{RESET}")
    print("All emails will be printed here - nothing is actually delivered.\n")
    sys.stdout.flush()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
        loop.close()


if __name__ == "__main__":
    main()
