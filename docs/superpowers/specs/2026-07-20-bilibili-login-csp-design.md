# Bilibili Login WebView CSP Fix

## Context

The native Bilibili login window opens but renders as an empty white page. The
top-level URL `https://passport.bilibili.com/login` returns valid HTML, but that
document loads its login JavaScript and CSS from `s1.hdslb.com`. Bilidown's
desktop CSP currently limits `script-src` and `style-src` to `'self'`, blocking
those required remote assets.

## Design

Extend the desktop CSP with the minimal Bilibili and HDSLB origins needed by the
external login WebView:

- allow `https://*.bilibili.com` and `https://*.hdslb.com` for scripts, styles,
  images, and network connections;
- retain `'self'` and the existing restrictive CSP directives;
- preserve the loopback-only backend connection rule and do not introduce
  wildcard origins outside Bilibili/HDSLB;
- retain the incognito login window and in-memory-only cookie import flow.

Add a focused configuration test asserting the required Bilibili/HDSLB CSP
directives are present and that unrestricted `https:` sources are absent.

## Alternatives Considered

1. **Targeted CSP allowlist (selected).** Restores the external login document
   while preserving the existing origin boundary.
2. **Open the system browser.** Rejected because Bilidown cannot then reliably
   collect its isolated HttpOnly login cookies.
3. **Allow all remote origins.** Rejected because it unnecessarily weakens the
   desktop WebView security policy.

## Verification

- Run the focused configuration test and the existing Python, TypeScript, and
  Rust checks.
- Build the Windows desktop executable and manually open the Bilibili login
  window. Confirm the login controls render, then close the incognito window
  without importing cookies.

## Scope

This is a desktop CSP correction only. It does not alter browser-cookie import,
cookie persistence, backend API authorization, or media-download behavior.
