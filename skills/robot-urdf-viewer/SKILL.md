---
name: robot-urdf-viewer
description: Generate a standalone, offline HTML robot viewer from URDF or Xacro, with simplified geometry, joint controls, and frame explanations. Use for inspecting robot structure and forward kinematics; excludes IK, physics simulation, and hardware control.
---

# Robot URDF Viewer

Build with the bundled converter and template. Preserve the two-tab interface: **Joints** for manual sliders and optional animation, **Frames** for the link tree and transform walkthrough. Keep technical details collapsed and animation paused on load.

## Generate

1. Locate the requested URDF and mesh packages. Expand Xacro using the project's ROS environment and required arguments first; never guess unresolved substitutions.
2. Choose the tip link from the request or robot structure. For multiple tools, use the requested tool; if unspecified, disclose the converter's deepest-link default. The tip affects only the marker, coordinates, and trail.
3. Run from this skill's directory:

   ```bash
   python3 scripts/build_viewer.py /path/to/robot.urdf -o /path/to/robot-viewer.html \
     --package robot_description=/path/to/robot_description --tip tool_link
   ```

   Omit optional flags when unnecessary. Add `--tip-at X Y Z` for a point expressed in the tip link's frame. See [input-support.md](references/input-support.md) for mesh resolution and supported inputs.

4. Inspect reported model notes. Resolve missing packages when available. Do not silently substitute joint types, invent limits, or describe bounding boxes as exact meshes.
5. Open the generated HTML locally and verify the controls below. Return a link to the HTML and identify material geometry approximations or unavailable browser validation.

## Constraints

- Reuse `assets/viewer.html`; it embeds Three.js and its MIT notice. Generated viewers need no server, network, ROS runtime, or build system.
- Preserve URDF origins, axes, limits, and mimic equations. Keep meters and radians internally; angle controls display degrees.
- No IK, workspace solver, collisions, dynamics, or robot commands. Motion is illustrative forward kinematics.
- Follow the source project's asset restrictions. HTML containing geometry derived from private CAD must remain local in an allowed, Git-excluded location. Never bundle private robot data in this skill or upload it for testing.
- Do not edit the source URDF to make a visualization work. Report unsupported inputs or ask for a required model choice.

## Verify

Run `python3 scripts/test_builder.py` after changing the converter or template.

For a generated viewer, check in a browser:

| Check | Expected |
| --- | --- |
| Load with network blocked | Robot renders; no page errors |
| Slider, Home, Play/Pause | Child subtree moves; limits and mimic relationships hold |
| Frames tab and selected link | Parent/child frames and URDF origin agree |
| Frame walkthrough Pause | Both frame explanation and joint animation stop |
| Fit view, orbit, zoom, narrow screen | Robot and controls remain usable |
| Fixed-only model | Renders without enabled motion playback |

`window.robotViewer` exposes model data, joint values, scene links, frame selection, and the tip position for numerical checks. It has no IK methods. Use synthetic/public fixtures for reusable tests.
