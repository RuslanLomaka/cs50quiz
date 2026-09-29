# Security policy

## Supported version

Security fixes are applied to the latest commit on `main`. This project has not published stable versioned releases yet.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use the repository's private [GitHub security advisory form](https://github.com/RuslanLomaka/cs50quiz/security/advisories/new). Include the affected route or component, reproduction steps, impact, and a minimal proof of concept. Do not include real user data.

You should receive an acknowledgement within seven days. A validated issue will be triaged before details are published.

## Security boundaries

- The server, not the browser, calculates scores and decides whether an attempt is recorded.
- Quiz imports are size- and structure-limited. Source links accept only `http` and `https` URLs without embedded credentials.
- Production secrets and databases must stay outside Git.
- Logs must use identifiers and counts, never passwords, session cookies, raw quiz submissions, answer selections, or email addresses.
