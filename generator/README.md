# Profile card generator

Builds `assets/dark.svg` and `assets/light.svg`, the neofetch-style card on the profile page.

| File | What it does |
|---|---|
| `profile.py` | The copy. Edit lines here. |
| `stats.py` | Live GitHub numbers (stdlib only), with `cache/stats.json` as a fallback. |
| `layout.py` | Character-grid line builders (dot leaders, rules, uptime). |
| `render.py` | SVG output: themes, embedded Geist Mono, stream-in animation. |
| `make_assets.py` | One-off: portrait → `portrait.txt`, font subsetting. |

```bash
python -m pytest                                   # tests
GITHUB_TOKEN=$(gh auth token) python -m generator.build
python -m generator.build --offline                # cached stats only
pip install pillow fonttools brotli && python -m generator.make_assets   # new photo or new glyphs
```

A line that doesn't fit its 62 columns fails the build instead of rendering broken. Geist Mono is licensed under the SIL OFL 1.1 (`fonts/OFL.txt`).
