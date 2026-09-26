# MoveIt mock motion demo

| Component | Setup |
| --- | --- |
| Planning group | `arm`: `base_link` → `tool0`, six joints |
| IK | MoveIt's KDL plugin for tool-position goals |
| Planner | OMPL RRTConnect |
| Search budget | 60 seconds, one attempt; path validation adds time |
| Execution | ros2_control `mock_components/GenericSystem`; no physics or hardware driver |
| Obstacles | Three fixed 8 cm blocks staggered around the wrist's sweep |
| Demo limits | 1.0 rad/s, 1.0 rad/s² (provisional); RViz and script default to 100% scaling |
| Collision exception | Elbow ↔ wrist roll only; reviewed source-CAD overlap remains unresolved |

The launch adds mock control and nonzero speed limits in memory; the source URDF
retains its unverified hardware limits. Meshes stay local under `cad/`.
These demo values are not measured hardware ratings: the
[upstream Arctos configuration](https://github.com/Arctos-Robotics/ROS/blob/main/arctos_config/config/joint_limits.yaml)
disables arm velocity and acceleration limits and does not establish usable maxima.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arctos_ws
colcon build --packages-select arctos_moveit_config
source install/local_setup.bash
ros2 launch arctos_moveit_config demo.launch.py
```

In another sourced terminal, plan around the blocks and execute on the mock robot:

```bash
ros2 run arctos_moveit_config plan_blocks.py --execute
# Return along a newly planned path.
ros2 run arctos_moveit_config plan_blocks.py --execute --target home
```

Headless: launch with `rviz:=false` and plot the planned tool path instead.

```bash
ros2 launch arctos_moveit_config demo.launch.py rviz:=false
ros2 run arctos_moveit_config plan_blocks.py --plot /mnt/c/Users/<user>/OneDrive/Documents/arctos_tool_path.png
```

| `--plot` output | Source |
| --- | --- |
| `tool0` path (blue), start/goal | MoveIt `/compute_fk` at every validated sample, `base_link` frame |
| Grey boxes | `config/blocks.yaml` |

Omit `--execute` to preview only. The script checks start/goal validity, reports
contacts on direct joint interpolation, and checks the timed path at joint-space
intervals no larger than 0.01 rad before execution. This is sampled validation,
not a continuous collision proof. A rejected path is not executed.

In RViz's MotionPlanning panel, select group `arm`, set the start to the current
state, and choose `home` or `across_blocks` as the goal. Use **Plan**, then
**Execute**. The tool marker uses KDL for interactive pose goals. The extra script
validation applies to the script; RViz uses MoveIt's configured validation.

Collision checking uses the reduced meshes from `arctos_description`; visuals retain
the original detail. Only the seven structural links are modelled; motors, cables, and the gripper
are omitted. Adjacent-pair exclusion is a demo assumption, not a physical-fit fix.

References: [KDL configuration](https://moveit.picknik.ai/main/doc/examples/kinematics_configuration/kinematics_configuration_tutorial.html),
[MoveIt planning scene](https://moveit.picknik.ai/main/doc/examples/planning_scene/planning_scene_tutorial.html).
