BANKVAULT BUG HUNT — INTENTIONALLY VULNERABLE LAB COPY
======================================================

IMPORTANT
- This copy contains intentional vulnerabilities for an authorized TechFest exercise.
- Run only on isolated lab machines / localhost, with fictional data.
- Do NOT deploy or expose this version to the public internet.
- Keep your original clean ZIP untouched.

Five seeded challenges
1. IDOR: transaction-details lookup does not verify transaction ownership.
2. SQL Injection: /challenge/search uses unsafe string interpolation in SQL.
3. Stored XSS: profile name is rendered using Jinja's |safe filter.
4. Authentication/session: logout accepts GET, allowing a state-changing GET/logout-CSRF scenario.
5. Sensitive information exposure: /challenge/diagnostics exposes fictional demo usernames, names, account numbers, and balances.

Useful routes
- /challenge/search?q=test (login required)
- /challenge/diagnostics (no login required)
- Transaction detail links from the transaction history page
- Profile page to test the stored-XSS challenge
- /logout can be called using GET

Restore procedure
Use the original clean BankVault ZIP to reset. Do not use the vulnerable database for anything real.
