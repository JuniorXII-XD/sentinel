# Manual browser QA checklist

Status: desktop Login was inspected at 1363 × 936. Authenticated browser flows and mobile viewports remain **not executed**. API and jsdom tests do not replace these checks.

Run locally with an account you create yourself. Use synthetic data, never credentials or sensitive real events, in screenshots.

| Check | Desktop 1440×900 | Mobile 390×844 | Expected |
| --- | --- | --- | --- |
| Login keyboard navigation / show password | Pending | Pending | Labels, focus and submission work |
| Failed login feedback / retry limit | Pending | Pending | Generic errors, readable 429 |
| Overview live/demo separation | Pending | Pending | Label and values match selected API scope |
| Mobile drawer close/navigation | N/A | Pending | Menu opens, route selection closes, background overlay closes |
| Chart/table readability | Pending | Pending | Charts fit; wide tables scroll within panel |
| Event search and filters | Pending | Pending | Correct rows, page reset, empty/loading/error states |
| Alert note / status / stale edit | Pending | Pending | Note persists, history grows, stale changes receive 409 |
| Analyst controls | Pending | Pending | No admin edit form; direct API denied |
| PDF / CSV download | Pending | Pending | File opens and matches report scope/period |
| Logout / browser back / expired session | Pending | Pending | Protected API returns 401; UI returns to Login |
| Keyboard-only / zoom 200% | Pending | Pending | No unreachable controls or hidden focus |
| Reduced-motion preference | Pending | Pending | Nonessential motion disabled |

Suggested portfolio screenshots after completing these checks: Overview with Demo banner; filtered repeated failures; Alert evidence and history; Reports summary; mobile Overview. Current `login-desktop.jpg` is an actual captured Login screen, not a generated design.

No screenshots of authenticated pages have been fabricated. The local browser tooling required user-controlled credential entry, so automated authenticated UI inspection was not completed.
