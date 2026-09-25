# Input support

| Input | Handling |
| --- | --- |
| Expanded URDF | Python 3 standard library; no extra packages |
| Xacro | Expand separately: `xacro robot.urdf.xacro -o /tmp/robot.urdf` with the project's required arguments |
| Fixed, revolute, continuous, prismatic joints | Preserved, including branching trees and chained mimic equations |
| Floating, planar, closed loops | Rejected with an explanation |
| Revolute/prismatic limits | Explicit finite lower/upper required; equal bounds produce a disabled slider |
| Continuous joints | One-turn slider/animation window; joint remains identified as continuous |
| Box, cylinder, sphere | URDF visual origin and dimensions preserved |
| STL (ASCII/binary), OBJ | Local mesh bounds and scale, then visual origin; shown as boxes |
| DAE and other meshes | Reported and omitted; use supported visuals or accept the approximation |
| No usable visuals | Automatic connectors between joint frames |
| Materials | RGB colors retained; textures and material alpha omitted |

Mesh lookup: explicit `--package NAME=PATH`, sourced ROS `AMENT_PREFIX_PATH`, then nearby package folders. Relative filenames resolve beside the URDF; `file://` paths are local. No remote asset downloads. Use `--strict-meshes` to fail on unsupported or unresolved meshes.

Keep expanded Xacro beside its source when relative mesh paths require that directory, or rewrite those paths to absolute local paths in a temporary copy. Do not change the original source.

The converter validates a single connected link tree, unique identifiers, finite values, nonzero joint axes, limits, and mimic references. Link/joint identifiers accept letters, digits, underscores, dots, slashes, colons, and hyphens.

Transform order follows [URDF's joint definition](https://docs.ros.org/en/fuerte/api/urdf_interface/html/index.html): parent frame → fixed origin (`Rz(yaw) Ry(pitch) Rx(roll)`) → motion about/along the joint-local axis → child frame. Visual origins affect geometry independently of joint frames.
