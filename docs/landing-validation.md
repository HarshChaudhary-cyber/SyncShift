# Landing campus implementation and verification

Date: 2026-10-05. Branch: `codex/landing-campus-experience`, based on the existing responsive-workspace commit `7c9d8bf`.

## Delivered

- Country-neutral landing page with the headline “Your university day, in sync.”
- Three accessible role views, a four-step explanation of the shared timetable, labelled synthetic product previews, supported AI copy, privacy boundaries, FAQs, and existing sign-in/account routes.
- Original procedural academic building, library, teaching pavilion, courtyard, paths, and trees. Role selection changes building accents and gently changes the scene angle.
- Server-rendered HTML content and original SVG campus available before the dynamically imported client-side WebGL scene loads. A static-view control, rendering error boundary, and context-loss handler preserve a usable page.
- Existing theme integration, visible keyboard focus, arrow/Home/End role navigation, reduced-motion preferences, normal vertical scrolling, and an internally scrollable example calendar.
- Demand rendering, offscreen/hidden-tab suspension, a capped pixel ratio, simplified small-screen geometry, and no shadow maps or postprocessing. The SVG remains visible when rendering is paused.

The [feature-to-source checklist](landing-product-audit.md) records implemented and conditional features and unsupported claims removed. Removed content includes regional legal/work/visa positioning, unsubstantiated pricing promises, testimonials/statistics, and absolute parsing/conflict claims. No provider-login buttons were introduced. Account creation uses the existing `/signup`; university membership is assigned separately.

## Files and dependencies

| Files | Purpose |
| --- | --- |
| `app/app/page.tsx` | Public entry point and neutral page metadata |
| `app/components/landing/LandingExperience.tsx`, `landing.css` | HTML content, responsive layout, role/preview controls, light/dark styling |
| `CampusScene.tsx`, `CampusView.tsx` | Lazy WebGL rendering, role transitions, visibility and failure handling |
| `CampusIllustration.tsx`, `campus-model.ts` | Original shared procedural geometry and local SVG fallback |
| `useCampusPreferences.ts` | Operating-system and existing application reduced-motion preferences |
| `app/package.json`, `app/package-lock.json` | Pinned necessary 3D dependencies |
| `docs/landing-product-audit.md`, this report, `docs/screenshots/landing/*` | Source audit and verification evidence |

The ten superseded components under `app/components/landing` were removed. Authenticated components, backend code, login implementation, permission checks, and database schema were not changed. Existing unrelated work was preserved.

Added `three@0.186.1`, `@react-three/fiber@9.8.1`, and development types `@types/three@0.186.0`. These packages use the MIT licence. Installed React is 19.2.8; Fiber 9 supports React 19 ([official installation guidance](https://r3f.docs.pmnd.rs/getting-started/installation)), and the installed peer dependency range was checked. Drei was unnecessary. Existing Framer Motion, Heroicons, fonts, and theme code are reused. No external models, textures, photos, testimonials, or private account screenshots were used. No reference video was supplied.

## Completed checks

| Check | Result |
| --- | --- |
| Frontend lint | Passed: 0 errors, 178 warnings in the existing codebase |
| Production build | Passed, including route generation; existing Google font fetch required network access |
| Existing frontend tests | 14 passed |
| Landing widths | 360, 390, 768, 1024, 1366 CSS pixels, in light and dark mode |
| Additional narrow desktop layouts | 1093 and 911 CSS pixels in both themes, corresponding to the available width of a 1366-pixel window at 125% and 150% zoom |
| Overflow measurements | Document scroll width equals client width in recorded checks; no uncontained right-edge offenders over the 1-pixel rounding tolerance. Root horizontal overflow is visible, so clipping does not conceal failures |
| Role controls | Click selection plus arrow/Home keyboard selection verified; selected state, focus, HTML content, and scene changes checked |
| Product previews | Dashboard, Calendar, Classes, and Planner selected at 390 pixels; no document overflow |
| Navigation | Section links, FAQ expansion with Enter, existing sign-in and account-creation pages verified |
| Reduced motion | Existing account preference set to reduced motion, saved, and observed on both campus views; original follow-system setting restored |
| Static fallback | Manual static-view control verified. Temporarily injected a renderer-initialization exception: the error boundary retained the SVG, headline, and sign-in link. Injection removed before final lint/build |
| Visibility | Offscreen inactive state observed. Hidden-tab handling reviewed in source |

Browser measurements are saved in [checks.json](screenshots/landing/checks.json). Viewport overrides use physical pixels on this Windows browser; the recorded `width` and `height` are actual CSS viewport dimensions. The browser sometimes reported a stale intersection state after a viewport override; a fresh mobile load rendered the compact WebGL scene correctly. The pause fallback also preserves an illustration in that state.

### Authenticated regression smoke checks

Used the existing isolated local demo database. Student and professor sign-in succeeded; the existing super-admin session was also exercised. Checked dashboard, calendar, classes, class detail, profile, planner, and notifications for all three roles; additionally checked university settings and timetables as super-admin. Opened and closed the role-specific AI panel for each role without submitting AI actions. Sign-out and public sign-in/sign-up navigation still work.

[Authenticated observations](screenshots/landing/authenticated-checks.json) include 25 route observations including rechecks. Initial rapid navigation showed a fetch error on admin notifications and the student dashboard. After waiting/revisiting, both loaded without alerts; initial and successful recheck records are retained. These are route/rendering smoke checks, not exhaustive backend mutation or permission tests.

## Screenshots

- [Desktop dark, 1366 × 800](screenshots/landing/desktop-dark.jpg)
- [Desktop light, 1366 × 800, showing the static pause fallback](screenshots/landing/desktop-light.jpg)
- [Mobile dark, 390 × 1000](screenshots/landing/mobile-dark.jpg)
- [Mobile manual static view, 390 × 1000](screenshots/landing/mobile-static.jpg)
- [Professor role with reduced motion, 1366 × 800](screenshots/landing/roles-reduced-motion.jpg)

Screenshots contain only public illustrative content. The mobile image covers the upper page; the document continues scrolling below it.

## Remaining verification limits

- Native browser zoom at 125%/150% was not directly controlled; equivalent CSS widths were checked instead.
- No real mobile device, GPU driver failure, actual WebGL context loss, hidden-tab timing measurement, or operating-system reduced-motion toggle was exercised. Renderer initialization failure and the existing saved reduced-motion preference were tested as described above.
- No Lighthouse/Core Web Vitals, FPS, bundle-transfer, screen-reader, or low-end hardware benchmark is claimed.
- Authenticated routes were smoke-tested on desktop during this landing task. The earlier responsive workspace work remains in the base commit.

No merge or deployment is part of this change.
