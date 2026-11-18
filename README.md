# Three.js reconstruction miner

For each prompt image this miner requests Three.js drafts through the witness, renders and compares them with the
image, improves the leading candidates round by round and hands back a single module inside the per-prompt limits.

Entry point: `main.py` -> `async generate(image, seed, witness) -> str | None`. The plan is in `miner404/versions.py`.

## Live run

```sh
uv venv --python 3.13 .venv-live
uv pip install --python .venv-live/bin/python -r requirements.txt
git clone --branch miner-runtime-v0.1.5 --depth 1 https://github.com/404-Repo/404-gen-subnet.git ../404-sdk
```

Create `witness.json` next to `main.py`, with `witness_url` set to `https://witness.subnet404.xyz` and
`proof_parameters` set to the absolute path of `404-sdk/witness-server/verifier/params`. Then:

```sh
.venv-live/bin/python main.py --prompts prompts.txt --seed PUBLISHED_SEED --wallet-name NAME --wallet-hotkey HOTKEY
```

## Changes in this version

- Output rules of 18.11: the model is centered at the origin, scaled uniformly into the unit cube, Y-up and facing +Z as
  the model built it. The final stretch, the forward push, the flat-object tilt, the photo tilt, the pose turn and the judged
  tilt are all off (`NO_ROTATION`, plan `stretch=0`, `forward=False`, `pose=False`, `judged_tilt=False`). The fit still
  measures the object's real outline (transforms baked into the vertices) before the uniform scale.

- `-x ** y` repair: `miner404/powfix.py` parenthesizes a unary operator before `**` (strings and comments skipped) after
  the regex repair; a module that already parses is returned unchanged.
