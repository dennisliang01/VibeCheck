# Accessibility (WCAG 2.1 AA baseline)

This document describes the accessibility measures implemented in VibeCheck and how to test them.

## WCAG 2.1 AA items addressed

- **Keyboard accessibility:** Skip-to-content link, all interactive elements reachable and operable via Tab/Shift+Tab/Enter/Space. Visible focus styles (focus-visible ring) on buttons, links, and form controls. No focus removed or hidden.
- **Semantics and structure:** Correct HTML elements (button for actions, a for navigation). One `<h1>` per page; logical heading order (h1 → h2). Landmark regions: `<header>`, `<main id="main-content">`, and content sections.
- **Names, roles, values:** Accessible names for icon buttons (aria-label). Form inputs have associated `<label>` (visible or sr-only). Native semantics preferred; aria-describedby used for error/help text where needed.
- **Color and non-color cues:** Validation/status (toast, score) includes text or icon, not color alone. Contrast: theme CSS variables (--text on --bg, --muted, --error, --success) should be verified to meet AA (4.5:1 normal text, 3:1 large)—run a contrast checker on key screens.
- **Screen reader support:** Toast uses `role="alert"` and `aria-live="assertive"`; success/error indicated by text prefix. Async status (upload, grading) reflected in button labels and toast. Meaningful images (if any) have alt text; decorative images use empty alt.
- **Motion:** `prefers-reduced-motion: reduce` respected: non-essential animations disabled in CSS; smooth scroll replaced with instant when reduced motion is preferred.
- **Error handling:** Form errors have an `id` and are linked via `aria-describedby` on the relevant control. First error receives focus on submit when validation fails.

## Known limitations

- **Code panel resizer (Learn page):** The splitter between the code panel and the question panel is mouse-only (drag). Keyboard users can collapse/expand the code panel via the toolbar buttons. Documented here for transparency.

## How to test

### Keyboard

1. **Skip link:** From a full page load, press Tab once. The first focusable element should be “Skip to content”. Activate it with Enter; focus should move to the main content and the skip link should be visible while focused.
2. **Full tab order:** Tab through the entire page. Every button, link, and form control should receive visible focus (ring). Use Shift+Tab to go backward. No focus traps; focus should not disappear.
3. **Activation:** Buttons and links should activate with Enter. Buttons also with Space. No control should require mouse-only interaction (except the code panel resizer, see above).

### Screen reader (quick check)

1. **Landmarks and headings:** Navigate by landmarks (e.g. “main”) and by headings (h1, then h2). Each page should have one h1; headings should follow a logical order.
2. **Forms:** On the home page, the upload control should be announced with its label (e.g. “Upload code” or file input label). On the Learn page, the answer textarea should be announced with its label. When an error is shown, it should be announced (toast and/or inline error).
3. **Toast:** Trigger a success or error toast (e.g. upload without file, or load sample). The message and type (Success / Error) should be announced.

### Reduced motion

1. Enable “Reduce motion” in your OS (e.g. Windows: Settings → Accessibility → Visual effects; macOS: System Preferences → Accessibility → Display).
2. Reload the app. Hero and reveal animations on the home page should not run (or should be minimal). Smooth scroll after upload should be instant.
3. Arrow animation on the home page (if any) should be disabled or reduced.

### Automated checks

- **Lint:** Run `npm run lint`. The project uses `eslint-plugin-jsx-a11y`; fix any reported a11y violations.
- **Tests:** Run the accessibility-related tests (e.g. `npm test` or `npm run test`). The test suite includes checks for roles, labels, and basic keyboard/semantic flow for the upload and Learn Q&A flows.
