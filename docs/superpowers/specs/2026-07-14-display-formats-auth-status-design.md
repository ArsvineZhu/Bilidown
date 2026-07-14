# Bilidown Display, Format, and Authentication Status Enhancements

## Goals

- Show trusted Bilibili cover images in the preview.
- Omit page suffixes unless a multi-page video is downloaded as multiple pages in one job.
- Improve Chinese and technical-text readability without external fonts.
- Preserve distinct Bilibili quality variants, including high-bitrate, 4K, HEVC, AV1, HDR, Dolby, and source audio when the current account can access them.
- Verify browser and uploaded Cookie authentication and show the account nickname and membership label.

## Backend Design

Trusted Bilibili and hdslb cover URLs are normalized to HTTPS in the resolve response. An untrusted preview URL becomes `null` without blocking video or audio resolution; cover download validation remains strict.

Each video-only yt-dlp format becomes a `QualityOption`. Its non-secret `format_id` is the option ID, and the response retains the Bilibili format name, quality code, codec family, bitrate, frame rate, and dynamic range. Multi-page selection intersects exact option IDs. Video jobs accept `quality_id` and `video_mode`; legacy `quality_height` remains a compatibility fallback.

`compatible_mp4` selects the requested H.264 SDR stream plus the best AAC stream and remuxes to MP4. `source_auto` selects the exact requested stream plus the best source audio and lets yt-dlp/FFmpeg choose MP4 or MKV without transcoding. Audio modes are best source, AAC/M4A, and MP3 VBR V2; legacy `original` maps to AAC/M4A.

`POST /api/auth/status` reuses the selected yt-dlp Cookie source and calls Bilibili's navigation endpoint. It returns only guest/active/inactive state, nickname, active-member boolean, and the Bilibili membership label. Cookie-loading and upstream failures remain structured errors, are redacted, and do not block ordinary resolution.

## Frontend Design

The authentication panel checks status when a source is selected, a profile is changed, or a Cookie file is uploaded, and exposes a manual refresh action. It distinguishes checking, guest, active, inactive, and failed states. It shows the source, nickname, and membership label, but not UID, avatar, expiry, or Cookie data.

The video panel defaults to compatible MP4 and shows exact common format variants. Source mode exposes all codecs and dynamic ranges. Labels include Bilibili quality name, codec family, frame rate when notable, bitrate, and HDR/Dolby indicators. Audio defaults to AAC/M4A.

Chinese UI text uses a modern local sans-serif stack, display Latin text uses Times New Roman, and technical metadata uses a local monospace stack. Core text is at least 14px and technical text at least 12px.

## Naming and Compatibility

Audio and video filenames include `Pxx` and the page title only when the resolved video has multiple pages and the current job requests multiple pages. Cover naming is unchanged. Existing collision handling remains responsible for suffixing repeated single-page downloads.

Existing API clients may continue sending `quality_height` and `audio_format=original`. No signed media URLs, Cookie values, or full account records are exposed.

## Verification

Backend tests cover cover normalization, naming combinations, exact format variants and selectors, compatibility fallbacks, audio modes, account states, errors, and redaction. Frontend tests cover authentication state transitions, format-mode filtering, advanced labels, and existing flows. The full backend, frontend, build, and Playwright suites run before release.

The public network acceptance video is `BV1ACNJ6VEwP`; it must show its HTTPS cover, remain capped at its actual 1080P source, use the simplified filename, and download compatible MP4 plus source audio. The authenticated 4K acceptance video is `BV1NGZtBwELa`; with an active member account it must expose 2160P H.264, HEVC, AV1, Dolby Vision, and the separate 1080P high-bitrate variants. Member-only and 4K smoke tests require an explicitly supplied authenticated account.
