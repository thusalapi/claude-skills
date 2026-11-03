# Spec reference

A spec is one JSON file per episode. Paths are relative to the spec file.

## Top level

| Field | Required | Meaning |
| --- | --- | --- |
| `slug` | yes | Build folder name (`build_<slug>`), holds cached voice lines and scene renders |
| `output` | yes | Path of the final MP4 |
| `scenes` | yes | List of scenes, played in order |
| `episode` | no | Shown as "No. 01" in the header and on the cover |
| `title` | no | Fallback cover title |
| `voice`, `speed`, `lang` | no | Kokoro voice (default `af_heart`), speed (1.08), language (`en-us`) |
| `brand` | no | See below |
| `music` | no | `{"file": "track.m4a", "loop": [start_s, end_s], "gain": 0.3}`. File is looked up next to the spec, then in the assets `sounds` folder |
| `cover` | no | See below |
| `sfx_hit`, `sfx_gain` | no | Override the transient offset or level of an effect, by name |

## `brand`

```json
"brand": {
  "name": "Acme Furniture",
  "series": "Acme Explains",
  "logo": "logo.png",
  "colors": { "bg": "#0D241B", "bg2": "#163628", "text": "#F4EEE2", "accent": "#CDAC70", "card": "#FAF7F0" },
  "fonts": { "serif": "fonts/MySerif.ttf", "serif_italic": "fonts/MySerif-Italic.ttf" },
  "tint": [1.03, 1.0, 0.94]
}
```

Without a logo, the end card and cover show `name` in the serif font. `tint` is the RGB multiplier of the footage grade.

## Scene

| Field | Meaning |
| --- | --- |
| `id` | Unique id, used by `--only` |
| `vo` | Voiceover line. Scene length = voice length + 0.15 s + `pad` |
| `pad` | Seconds after the voice ends (default 0.5) |
| `footage` | `[[path, start_s, share], ...]`. Shares split the scene between clips. Still images work too |
| `fit` | `true` shows the whole frame over a blurred fill (use for photos and 16:9 clips) |
| `dim`, `focus_x` | Darken footage (0 to 1), horizontal crop position (0 left, 1 right) |
| `label` | Small tracked label under the header, for example "Point 01 / 03" |
| `headline` | `[["Line one", false], ["accent line", true]]`. `true` = italic accent colour |
| `headline_at`, `headline_y` | Reveal start time and top position |
| `captions` | `false` hides captions for this scene |
| `caption_skip_words` | Number of leading words left out of captions |
| `overlays` | List of overlays, see below |
| `sfx` | `[[seconds, "name"], ...]` |
| `still_at` | Time used for the contact sheet (default 80% of the scene) |
| `end` | End card instead of normal content: `{"headline": [...], "button": "...", "contact": "...", "sub": "...", "chat_icon": true}` |

## Overlays

| `type` | Fields |
| --- | --- |
| `kicker` | `text`, `start`, `y`. Centred tracked caps between two drawing rules |
| `bignumber` | `text`, `start`, `y`, `size`. Large accent-colour number or short text |
| `measure` | `value`, `unit`, `start`, `y`. Dimension line with a counting number |
| `bullets` | `items`, `starts` (one time per item), `y` |
| `tag` | `text`, `start`, `y`. Small left-aligned label |
| `layers` | `base_label`, `top_label`, `base_color`, `top_color`, `base_at`, `layer_at`. Isometric two-layer diagram with callouts |

## `cover`

```json
"cover": {
  "lines": [["What is", false], ["cold brew?", true]],
  "kicker": "Acme Explains",
  "sub": "3 things to know before you buy",
  "frame": ["clips/workshop.mp4", 6.0],
  "focus_x": 0.45,
  "size": 150
}
```

Without `frame`, the first scene with footage is used. Without any footage, the brand gradient is used.
