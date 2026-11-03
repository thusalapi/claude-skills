# Claude Skills

Skills I built and use with [Claude](https://claude.ai) to automate real work. Each skill is a folder with a `SKILL.md` (the instructions Claude follows), plus any scripts and reference files it needs. They follow the open [Agent Skills](https://agentskills.io) format.

| Skill | What it does | Highlights |
| --- | --- | --- |
| [explainer-reel](skills/explainer-reel) | Turns a script and real footage into a finished 9:16 education video with a crop-safe cover | Python, FFmpeg, NumPy, offline TTS, audio mastering |

More skills are on the way: a job application assistant and a daily social post writer.

<p align="center"><img src="skills/explainer-reel/assets/demo.gif" alt="Explainer reel demo" width="220"></p>

## Install

**Claude Code**

```
/plugin marketplace add thusalapi/claude-skills
/plugin install explainer-reel@thusala-skills
```

**Claude app (claude.ai or desktop)**

Download a skill folder as a zip and upload it under Settings > Capabilities > Skills.

## What I learned building these

- A skill works best as a process with checkpoints, not a single prompt. The reel skill checks a cheap contact sheet before an expensive render, the same way a CI pipeline runs fast tests first.
- Good skills separate facts from instructions. Business facts live in a profile file, and the skill refuses to invent claims that are not in it.
- Moving deterministic work (rendering, mixing, measuring) into scripts keeps the model's job small and the output repeatable.

## Licence

MIT. See [LICENSE](LICENSE).
