# Episode 001: Fuel Oil Purifier in Google Flow

## Scope and source of truth

`examples/episode_001_flow.json` is the approved episode. Edit dialogue,
duration, visual action, camera and handoff there. Each build compiles the same
values into `script.json`, `storyboard.json`, `veo_prompts.json`, eight final
scene briefs, and `flow_jobs.json`. Old planning files are preserved once under
`flow_jobs/previous_planning/` when replaced. The previous LLM review is
archived; a score such as `REVISE 60/100` is not a render gate.

The exact final clip plan is 6 + 12 + 9 + 13 + 8 + 5 + 12 + 4 = **69 seconds**.
No generated video or image reference ships with this repository.

## On Windows

If you have not cloned the repository yet, use a folder you own (for example
`Documents`), then enter it:

```powershell
Set-Location (Join-Path $HOME "Documents")
git clone https://github.com/khoilm543171-source/ai-video-director.git
Set-Location ai-video-director
```

Otherwise, in PowerShell from your existing repository root:

```powershell
git pull
python -m pip install -r requirements-orchestrator.txt
powershell -ExecutionPolicy Bypass -File .\scripts\start_episode_001.ps1
```

Or compile just the spec:

```powershell
python scripts/build_flow_pack.py --episode-id episode_001_fuel_oil_purifier
python scripts/review_flow_prompts.py --episode-id episode_001_fuel_oil_purifier
```

The output folder is `outputs/episodes/episode_001_fuel_oil_purifier/flow_jobs/`.
The compiler does not require an LLM key and does not use Google credits.
If preflight fails, correct the named field in the spec and rebuild.

## In Flow

1. Create the three reusable reference assets from `reference_TinyCadet.txt`,
   `reference_ChiefEngineer.txt` and `reference_EngineRoom.txt`. Reuse the same
   assets and project across all eight scenes.
2. Read `scene_01.txt` for the final shot, then generate `scene_01_base.txt`.
   Compare face, PPE, set and voice to the approved brief before other scenes.
3. Repeat `scene_XX_base.txt` scene by scene. For `scene_02`, `scene_03`,
   `scene_04` and `scene_07`, extend **that scene's** base in Veo 3.1 Lite with
   its `scene_XX_extend.txt`. Never extend a scene into the next numbered one.
4. Export one final video per scene under `scenes/scene_01.mp4` through
   `scenes/scene_08.mp4`. Keep raw Flow renders separately so you can retry.
   Trim the tail only if every approved word/action remains intact. Check the
   resulting files against `flow_jobs.json`, then run `check_flow_clips.py`.

Google's [Flow model feature table](https://support.google.com/flow/answer/16352836?hl=en)
currently lists 8-second Ingredients/References generations on Veo 3.1 Lite
and Fast; Veo 3.1 Lite can extend 8-second clips. A textual request for exactly
9, 12 or 13 seconds is not a native duration control. The extension may have a
variable final length: inspect the download, and keep the correct 9/12/13
seconds when the final word and end pose fit. Scene 07 spans an extension
boundary in a single sentence; verify the voice and lip-sync across that
boundary. Regenerate that one scene if they do not match.

## Acceptance

```powershell
python scripts/check_flow_clips.py --episode-id episode_001_fuel_oil_purifier
```

The script requires eight distinct MP4s, exact planned lengths within a frame
tolerance, 9:16 video, and audio streams. Also perform a human pass:

If `ffprobe` is missing, install FFmpeg and make sure `ffprobe -version` works
in a new PowerShell window before rerunning the validator.

- All quoted dialogue, in speaker order, is audible verbatim; no repeated words
  at extensions; Chief's scene 07 nod follows the Cadet's last word.
- Tiny Cadet and Chief keep their faces, PPE and voices; Chief stays screen-left,
  Cadet screen-right; fuel and purifier stay oriented left-to-right.
- Scene 04 conveys only symbolic centrifugal separation of water and solids,
  without invented machinery internals. There are no captions or music.
- Final scene starts from the prior scene's end pose. Eight final files remain
  separate, with no crossfades or title cards.

An audio stream alone cannot prove that words or lip-sync are correct. Do not
publish or assemble the clips until the human pass succeeds. If native speech
fails, first regenerate the affected Flow scene. A separately recorded voice
is a fallback requiring a new lip-sync review and changes the stated native
audio requirement; do not silently substitute it.
