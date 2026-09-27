# Resources

| Resource | Use |
| --- | --- |
| [Arctos docs](https://arctosrobotics.com/docs/) | Assembly, setup, technical reference |
| [Arctos BOM](https://arctosrobotics.com/bom/) | Components and hardware |
| `cad/` | Purchased CAD/STLs: geometry, dimensions, joint placement for the URDF |
| [docs/BAMBU_CLI.md](docs/BAMBU_CLI.md) | `bambu-studio` in WSL; run from `cad/` so outputs (incl. `result.json`) stay there |
| [docs/PRINTING_GUIDE.md](docs/PRINTING_GUIDE.md) | Print baseline, profile differences, P1S settings |
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Current status, what's built, and why |

`docs/` is local-only (Git-ignored).

# Rules

- **Wait for the go-ahead.** When the user shares a goal or context, acknowledge and wait. Do only the step asked: no extra features, preemptive fixes, or scope creep.
- **Branch per change.** Before editing, ask the user what to name a new branch, then create it from up-to-date `main`. Commit and push each finished step to that branch without asking.
- **`main` is user-controlled.** Merge to `main` only when the user asks, then delete the branch locally and on GitHub. Ask before force-push, other branch deletion, or history rewrites.
- **Keep it lean.** Markdown: short, tables/visuals over prose. Comments: only non-obvious intent, units, assumptions, or constraints; state shared conventions once.
- **CAD stays local.** Reading, measuring, and deriving URDF geometry from `cad/` is allowed. Never commit, upload, or publish the CAD/STLs or their copies, archives, or mesh exports; keep derived meshes under `cad/`. Don't weaken the `cad/` and `arctos_cad/` Git exclusions.
