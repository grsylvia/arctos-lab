# Arctos description

Initial structural URDF from purchased v2.9.7 STLs, checked against STEP cylinder axes.
Mesh assets and generated exports stay local under Git-ignored `cad/`.

| Model property | Status |
| --- | --- |
| Geometry | Seven links using actual structural STLs; motors, fasteners, covers, and gripper omitted |
| Joint axes | Six axes located from bearing/shaft geometry; positive directions follow the right-hand rule |
| Zero pose | Supplied CAD assembly pose; hardware home and motor signs uncalibrated |
| Joint limits | Locked at zero; travel, effort, and velocity remain unverified |
| Physics | Visual model only; no collision or inertial model |
| Wrist fit | `B-core.stl` shifted +3 mm in X to align its bore with the carrier bores; assembly fit needs review |

Build and generate the local model:

```bash
# Enter the workspace containing the source package and private CAD.
cd ~/arctos_ws
# Load the installed ROS 2 Jazzy environment.
source /opt/ros/jazzy/setup.bash
# Build and install the robot description package.
colcon build --packages-select arctos_description
# Make the built package available to ROS commands.
source install/local_setup.bash
# Export link meshes locally using the measured geometry configuration.
ros2 run arctos_description prepare_meshes.py \
  --cad-root "$PWD/cad/2.9.7" \
  --geometry "$PWD/src/arctos_description/config/geometry.yaml"
# Expand the model with references to the private local mesh exports.
xacro src/arctos_description/urdf/arctos.urdf.xacro \
  mesh_dir:="$PWD/cad/2.9.7/urdf_meshes" \
  -o cad/2.9.7/urdf_meshes/arctos.urdf
# Validate the generated URDF and display its link hierarchy.
check_urdf cad/2.9.7/urdf_meshes/arctos.urdf
```

`config/geometry.yaml` records source filenames, assembly-frame origins in mm, axes,
and mesh alignment corrections. Re-run mesh preparation after changing geometry.
All link frames initially share the STL assembly orientation: Z up, X toward the tool.

| Joint | Axis | Source feature |
| --- | --- | --- |
| 1 | Z | X pulley shaft cylinders |
| 2 | Y | Y core and Z lower core bearing bores |
| 3 | Y | Z upper core and Z gearbox shaft bores |
| 4 | X | A inner/outer core cylinders |
| 5 | Y | BL/BR carrier and bevel gear bores |
| 6 | X | C core cylinders |

## View in RViz

```bash
# Load ROS and the built workspace.
source /opt/ros/jazzy/setup.bash && source ~/arctos_ws/install/local_setup.bash
# Start the model, joint state publisher, and RViz.
ros2 launch arctos_description display.launch.py
```

```mermaid
flowchart LR
  URDF[urdf/arctos.urdf] --> RSP[robot_state_publisher]
  JSP[joint_state_publisher_gui] -- /joint_states --> RSP
  RSP -- /robot_description, /tf --> RVIZ[rviz2 + rviz/display.rviz]
```

| Launch argument | Default | Use |
| --- | --- | --- |
| `model` | installed `urdf/arctos.urdf` | URDF file to display |
| `rviz_config` | installed `rviz/display.rviz` | RViz layout: grid, robot model, TF |
| `gui` | `true` | Joint sliders; `false` publishes zero joint states |

Sliders appear only for joints with a non-zero limit range.

Reference: [Arctos docs](https://arctosrobotics.com/docs/) and
[BOM](https://arctosrobotics.com/bom/). Geometry comes from local CAD; the BOM does
not establish joint limits. Verify travel and assembly fit before enabling motion.
