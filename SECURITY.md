# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately through GitHub: on the repository page, open **Security → Report a
vulnerability** (private vulnerability reporting). If that option is not available, send a
direct message to a maintainer listed in `.github/CODEOWNERS`.

Please include what you found, how to reproduce it, and what an attacker could do with it.
We aim to acknowledge reports within 3 working days and to agree a fix and disclosure date
with you.

## What counts

Anything that could make WeatherWise:

- send or show a wrong, misleading or unsafe warning (for example, prompt injection that changes
  a safety message, or a way to make "move now" appear without an official alert);
- expose personal data (locations, chat text, phone numbers) or credentials;
- run up cloud costs without limit (bypassing the chat limits or the daily cap);
- be taken over or made unavailable.

## Supported versions

Only the latest commit on `main` is supported.
