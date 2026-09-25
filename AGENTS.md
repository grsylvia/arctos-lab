Resource: [Arctos documentation](https://arctosrobotics.com/docs/)

# Project guidance

- Markdown documentation must be concise, simple, and light on text. Prefer tables and visualizations over paragraphs when presenting data.
- The agent is responsible for writing and modifying the Arctos project code.
- Code generation is user-driven. Keep generated code and code changes constrained to the user's provided instructions. Do not anticipate or preemptively address issues, add features, or expand scope beyond those instructions.
- CRITICAL: `cad/` contains non-public CAD purchased by the user. Keep it local and excluded from Git via `.gitignore`. Never stage, commit, force-add, upload, publish, or otherwise share these files, including copies, archives, or exports derived from them. Do not remove or weaken the CAD exclusions (`cad/` and its original name, `arctos_cad/`).
