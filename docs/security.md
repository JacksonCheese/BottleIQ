# Security and deployment

## Implemented controls

- Password signup/login with Argon2 hashing; 12–128 character passwords.
- Random 256-bit opaque sessions; only token digests stored; 12-hour expiry and server-side revocation at logout.
- HttpOnly, SameSite=Lax cookies. `COOKIE_SECURE=true` adds Secure cookies for HTTPS.
- Owner/admin writes, viewer reads. Tenant principal is resolved server-side; organization IDs cannot be supplied to switch customers.
- Store scoping for every analysis/import/order operation, tenant filters on detail lookups, and composite tenant foreign keys.
- Origin and Fetch Metadata checks on mutations; the same-origin Next proxy avoids permissive CORS.
- Body and CSV limits, bounded numeric/date parsing, no executing imported content, no retained uploaded file storage.
- Formula escaping for exported CSV strings.
- Generic login failures with dummy password verification for unknown accounts.
- Database-backed per-account login/signup/recovery/invitation throttles shared by API replicas; a process-local 20/minute source-IP guard remains a supplementary limit. Neither trusts arbitrary `X-Forwarded-For`.
- Single-use, 30-minute password reset tokens and seven-day organization invitations are stored only as hashes and sent by transactional SMTP. Password reset revokes sessions. Only owners can invite, and every role is fixed at acceptance.
- API response `no-store`, request IDs, `nosniff`; web frame-denial and referrer headers.
- Production startup refuses demo mode, insecure cookies, or missing SMTP configuration.
- Secrets, databases, upload directories, virtual environments, and build artifacts ignored by Git.

Demo access is explicitly gated by `DEMO_ENABLED`. The demo user's password is random and never printed. The public demo button signs into the synthetic demo organization. **Do not upload actual store data into that organization or enable demo mode on a pilot production instance.** Customer accounts are independently isolated.

## Before hosting actual pilot data

1. Deploy behind HTTPS with `ENVIRONMENT=production`, `COOKIE_SECURE=true`, `DEMO_ENABLED=false`, and `WEB_ORIGIN` set to the exact HTTPS frontend origin. Use private API/database networking and no publicly exposed database port.
2. Use a dedicated least-privilege database role, managed credentials, encrypted disk/backups, and a tested restore procedure. Compose's password is for local development only.
3. Configure ingress body and time limits. The per-account throttle is shared, but IP-based protection at the Next proxy and trusted ingress still matters against account rotation. Never simply trust caller-controlled forwarding headers. Periodically prune old `auth_rate_limits` rows in an operations job.
4. Configure and test SMTP delivery, recovery, and invitations. Staff removal, verified email, MFA, SSO, and session management remain future work. A managed OIDC provider is a possible later auth boundary.
5. Agree on retention/deletion procedures for uploaded business data and logs. There is no export-all/delete-account UI or complete user mutation audit trail in V1.
6. Review dependency updates and run tenant-boundary tests in deployment CI. Database RLS is not enabled; isolation relies on API scoping plus composite constraints. A separate read policy or RLS layer would strengthen defense in depth.

Tests cover anonymous access, cross-tenant store/vendor references, DB cross-tenant facts, role enforcement, CSRF checks, session revocation, rate limits, oversized uploads, and CSV escaping. They are useful evidence, not a security audit.

Known deployment gaps must not be described as implemented. This repository is suitable for local demonstrations and supervised validation. The production controls above require actual deployment and operational verification before live-store use.
