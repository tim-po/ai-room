Self-hosted variable Cyrillic fonts from the Google Fonts upstream repository, downloaded 2026-10-02:
- https://github.com/google/fonts/tree/main/ofl/manrope (Manrope.ttf)
- https://github.com/google/fonts/tree/main/ofl/golostext (GolosText.ttf)
Each family retains its accompanying SIL Open Font License. No third-party browser requests. Manrope is used by the interface; Golos Text is available for reading surfaces. The five branch illustrations and foundation orbit in atlas.js are original native SVG drawn for this application.

The .woff2 files are what browsers load: the same fonts subset to Latin, Cyrillic, punctuation, arrows and common symbols and compressed (fontTools `pyftsubset --flavor=woff2 --layout-features='*' --unicodes=U+0000-017F,U+0400-04FF,U+2000-27BF`). The .ttf files remain as the source and as a fallback.
