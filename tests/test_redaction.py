from bilidown.redaction import redact_message


def test_redacts_cookie_values_and_signed_urls() -> None:
    value = "SESSDATA=secret https://cdn.example/video?deadline=1&upsig=secret"
    redacted = redact_message(value)
    assert "secret" not in redacted
    assert "SESSDATA=<redacted>" in redacted
    assert "<signed-media-url>" in redacted

