---
name: explainer-reel
description: Make short 9:16 education videos (Reels, Shorts, TikTok) for a small business from its real footage or photos, with motion graphics, an offline AI voice, captions, a mixed soundtrack and a crop-safe cover. Use when the user asks for an explainer video, the next episode of a video series, a reel cover or thumbnail, or a change to an existing episode.
---

# Explainer Reel

Produces a 30 to 45 second vertical "explains" episode from a JSON spec, using `scripts/reel.py`. The video teaches one useful thing about the business's field and ends with one clear call to action. The look is calm and premium: serif headlines, tracked labels, real footage in a feathered band, words lighting up as they are spoken.

## Before writing anything

1. **Load the brand profile.** Ask for the business's profile, or help the user fill `references/brand-profile-template.md` once and save it with their project. It holds products, audience, voice, contact line, brand colours and the facts the business has confirmed. Never invent facts that are not in it.
2. **Collect the media.** Real footage clips and product photos, plus the logo (PNG with transparency is best). Ask the user to attach them or point to a folder.
3. **Set up the toolkit once per environment:** `bash scripts/setup_assets.sh`. It installs the Python packages, downloads the Kokoro voice model and the fonts, and generates a licence-free sound-effect kit. Needs `ffmpeg`.

## Script formula (6 to 8 scenes)

1. **Hook, 0 to 2 s.** A question to the viewer, a common mistake, a number ("3 things to know before...") or a contrarian line. It appears as the headline, never twice.
2. **Open loop, 2 to 6 s.** Promise a payoff ("Number three surprises most people").
3. **Points.** One idea per scene, labelled "Point 01 / 03". New visual every 2 to 3 seconds (a cut, an overlay or a counter).
4. **Proof.** Real footage of the team, the process or the product.
5. **CTA.** One action with one contact route, taken from the brand profile.

Plain words in the voiceover. Short sentences. No hype or stock AI phrases.

## Truth rules (never break)

- Anything shown as the business's own work must be its real footage or photos. AI-generated images are illustration only and are never presented as the business's product.
- Technical, health, safety or performance claims need a source: the brand profile, a supplier data sheet, or the user's confirmation in chat.
- Prices, sizes and specifications come from the brand profile and are confirmed before use.
- Never post or schedule anything without the user's approval of the video, caption, date and time.

## Building an episode

1. **Write the script** per the formula. Share it for review first if the user wants.
2. **Write the spec.** Copy `examples/demo/demo.json` and edit. The full field list is in `references/spec-reference.md`. Brand colours, series name and logo go in the `brand` block. Check clip lengths with `ffprobe` so each `start + scene length` fits inside the clip.
3. **Look before rendering.** `python3 scripts/reel.py ep.json --stills check.jpg`, then open the contact sheet. Fix overlapping or clipped text, repeated text and empty areas before a full render. A full render takes several minutes, a contact sheet takes seconds.
4. **Make the cover.** `python3 scripts/reel.py ep.json --cover cover.jpg` also writes `cover_crops.jpg` with the full, 4:5 feed and 1:1 grid crops. Check that the title is whole in all three.
5. **Render.** `python3 scripts/reel.py ep.json`. Use `--only s3,s4` to re-render single scenes after a fix. The voice is cached per line, so only changed lines are re-synthesised.
6. **Deliver** the MP4 and cover, then wait for approval before any posting.

## Design rules (built into the toolkit)

- Two background colours (gradient), one text colour and one accent colour, all set in `brand.colors`. Headlines use a serif, with the second line in the accent colour and italic.
- Footage sits in a feathered band (y 400 to 1500) with a warm grade, a slow 6% push-in and light film grain. Still photos use `"fit": true`.
- Captions are sentence case and brighten word by word. Turn them off (`"captions": false`) or skip leading words (`caption_skip_words`) where the headline already shows the same words.
- Motion is calm: masked line reveals, accent rules drawing in, counters and callouts. No shaking and no loud badges.
- Keep text inside 72 px side margins and clear of the bottom 250 px, where the platform's buttons sit.

## Covers

Platforms crop reel covers: 4:5 in the feed (y 285 to 1635) and 1:1 on the profile grid (y 420 to 1500). The toolkit keeps key text in the centre band, y 560 to 1360. A good cover has 2 to 5 big words (the topic as a question or promise), one short sub line, a real footage frame behind, and the logo card low down. No prices or small print. Once a series is running, make two cover versions and A/B test them.

## Sound

- Voice: Kokoro, offline. Default `af_heart` at speed 1.08. Alternatives: `am_michael`, `bf_emma`, `bm_george`.
- Effects: the generated kit (`whoosh`, `swipe`, `impact`, `thud`, `pop`, `click`, `tick`, `riser`, `ding`, `msg`). Cue them per scene with `"sfx": [[seconds, "name"]]`.
- Music is optional. Use only tracks with a licence that covers commercial social media use (for example a stock library that states this, or CC0). Never use commercial or trending songs.
- The mix ducks music about 55% under the voice and masters to -14 LUFS and -1.5 dB true peak, which suits Reels, Shorts and TikTok.

## Quality checklist before sending

- Hook readable in the first 2 seconds with the sound off.
- No sentence appears twice on screen at the same time.
- Every claim passes the truth rules.
- Text inside the safe margins. Cover title whole in all three crops.
- Contact details match the brand profile.
- 1080x1920, 30 fps, AAC audio, file under 30 MB (the toolkit caps video bitrate at 5 Mb/s).
