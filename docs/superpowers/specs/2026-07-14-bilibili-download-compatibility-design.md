# Bilibili Download Compatibility Fix

## Context

`BV1ACNJ6VEwP` exposes two compatibility failures in the current application:

- Bilibili returns its trusted archive cover as an `http://i0.hdslb.com/...` URL, while cover downloads currently require HTTPS and reject it.
- The pinned `yt-dlp==2026.6.9` receives HTTP 412 from Bilibili's WBI play URL endpoint. An isolated test with `yt-dlp==2026.7.4` resolves the same public video and exposes 360P, 480P, 720P, and 1080P formats.

## Design

Upgrade the pinned `yt-dlp` dependency to `2026.7.4`. Keep the existing extraction and download architecture unchanged.

Normalize cover URLs at the trust boundary:

- Continue accepting only `bilibili.com`, `hdslb.com`, and their subdomains.
- Accept only HTTP or HTTPS input URLs.
- Upgrade HTTP to HTTPS before making the request.
- Reject credentials, non-default ports, and every other scheme or host.
- Use the normalized HTTPS URL for both the request and extension detection.

This preserves the existing SSRF boundary while supporting Bilibili's normal metadata output. It does not add a generic HTTP fallback and does not follow untrusted cover hosts.

## Alternatives Considered

1. Disable cover URL validation. Rejected because it would turn metadata into an unrestricted server-side request target.
2. Permit HTTP downloads from trusted hosts without upgrading. Rejected because HTTPS is available for Bilibili archive images and avoids cleartext transport.
3. Keep the old `yt-dlp` and implement a custom Bilibili extractor fallback. Rejected because it duplicates fast-changing WBI logic already fixed upstream.

## Verification

- Unit tests cover HTTPS acceptance, trusted HTTP-to-HTTPS upgrade, and rejection of untrusted hosts, schemes, credentials, and ports.
- The existing backend suite must pass.
- A network smoke test with `BV1ACNJ6VEwP` must resolve available qualities.
- Live acceptance downloads the original cover, an audio stream, and a low-resolution video for that BV, then confirms output files are non-empty. Video probing is performed when bundled or system `ffprobe` is available.

## Scope

No API shape, frontend behavior, authentication storage, queue semantics, or output naming changes are included.
