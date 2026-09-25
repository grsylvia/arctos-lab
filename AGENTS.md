# Project resources

**Use these resources when developing Arctos code or making hardware-related decisions.**

| Resource | Use |
| --- | --- |
| [Arctos documentation](https://arctosrobotics.com/docs/) | Assembly, setup, and technical guidance |
| [Arctos bill of materials (BOM)](https://arctosrobotics.com/bom/) | Components and hardware requirements |
| Local CAD and STLs in `cad/` | Analyze geometry, dimensions, and joint placement to develop the URDF |

# Project guidance

- Markdown documentation must be concise, simple, and light on text. Prefer tables and visualizations over paragraphs when presenting data.
- The agent is responsible for writing and modifying the Arctos project code.
- Comment generated code and configuration for readability: place one short comment immediately above each statement or setting, using at most one sentence that fits on one line.
- Code generation is user-driven. Keep generated code and code changes constrained to the user's provided instructions. Do not anticipate or preemptively address issues, add features, or expand scope beyond those instructions.
- **Use the purchased CAD and STLs for local analysis and as source material for the URDF.** Reading, measuring, and processing them locally is authorized; the restriction concerns publishing the assets, not using them for development. Geometry measurements may inform URDF code.
- CRITICAL: Keep purchased CAD/STL assets and their copies, archives, and mesh exports local and excluded from Git; never publish them to GitHub or upload them to external services. Store derived mesh assets under `cad/` and reference them locally when needed. Do not stage, commit, force-add, or weaken the CAD exclusions (`cad/` and its original name, `arctos_cad/`).
