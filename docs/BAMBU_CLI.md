# Bambu Studio CLI in WSL

Agents can use `bambu-studio` through the shell for **local import, slicing, and export only**.

| Item | Installed setup |
| --- | --- |
| Version | Bambu Studio 2.8.2.61, Ubuntu 24.04 x86-64 |
| Command | `~/.local/bin/bambu-studio` (already on PATH) |
| Installation | `~/.local/opt/bambu-studio-2.8.2.61/` |
| Runtime | Extracted official AppImage plus user-local Ubuntu libraries; no FUSE or sudo needed to run |
| Model files and exports | Keep under Git-ignored `cad/` |
| Verified | CLI help and reading the existing P1S test project |

Run from the workspace:

```bash
# Display the installed CLI options.
bambu-studio --help
# Inspect the local project without slicing it.
bambu-studio --info cad/prints/Test_print_all.3mf
# Keep slicing outputs and any diagnostic files inside the private CAD directory.
cd cad/prints
# Slice all plates using the project's saved settings and export a new file.
bambu-studio --slice 0 --export-3mf Test_print_all-linux.gcode.3mf Test_print_all.3mf
```

| Agent workflow | Requirement |
| --- | --- |
| Input | Prefer a prepared 3MF with the intended printer, plate, and filament settings |
| This printer | P1S, 0.4 mm nozzle, Bambu PLA matching the spool |
| Output | Use a new filename; retain the original project |
| Success | Check exit status and confirm the exported archive contains plate G-code before calling it printable |
| Scope | Local files only; no printer connection, cloud upload, or print start |

The installation is local to this WSL user and does not travel with a Git clone. Download SHA-256 was checked against the [official release](https://github.com/bambulab/BambuStudio/releases/tag/v02.08.02.61).

Command reference: [Bambu Studio CLI documentation](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage).
