# Security policy

## Supported versions

Security fixes are applied to the latest released version. Users should upgrade
to the newest patch release before reporting an issue.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose API keys,
personal data, or systems running the optional HTTP service. Email
`chrisdimurro@gmail.com` with:

- the affected version and component;
- reproduction steps or a proof of concept;
- the likely impact; and
- any suggested mitigation.

You should receive an acknowledgment within seven days. Please allow time for a
coordinated fix before publicly disclosing the issue.

The calculation library is deterministic and does not transmit data. The optional
API and `clean_url()` process untrusted input and should be deployed with normal
network isolation, request-size limits, TLS, rate limiting, logging, and backups.
