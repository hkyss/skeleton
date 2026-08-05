## What and why

<!-- What changes, and what problem it solves. Link the issue if there is one. -->

## Ownership

<!-- Skeleton-owned or project-owned? See skeleton.manifest.json. Skeleton-owned changes reach every downstream project through skeleton.update, so say what those projects will see. -->

## Checks

- [ ] `devctl make verify` passes on the active preset
- [ ] Checked against the other presets, or the change cannot affect them
- [ ] Preset markers intact; new ones covered in `scripts/tests/test_preset_markers.py`
- [ ] No comments or docstrings added
- [ ] `skeleton.manifest.json` updated if files moved between ownership sides

## Notes for the reviewer

<!-- Anything non-obvious: a tradeoff you made, a case you deliberately did not handle, something you want a second opinion on. Delete if there is nothing. -->
