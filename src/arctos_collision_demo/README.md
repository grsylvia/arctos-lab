# Collision verification

```bash
source /opt/ros/jazzy/setup.bash
source ~/arctos_ws/install/local_setup.bash
ros2 launch arctos_collision_demo collision.launch.py
```

Move the joint sliders while watching the status above the arm.

| Display | Meaning |
| --- | --- |
| Blue block | No detected robot contact at the current pose |
| Red block / red dots | Block collision / contact locations |
| `Self: CONTACT` | Structural meshes intersect; contacting pairs are listed |
| Waiting for current joint states | No complete recent joint state; no clear result is asserted |

Three fixed 8 cm blocks are checked using MoveIt's collision engine and the local
URDF collision meshes (the locally simplified set). No link pairs are excluded, including adjacent assembly parts.
This checks the displayed pose, not the swept path between slider updates.
Sliders remain free to move through obstacles. No physics or hardware control runs.
Only the seven modelled structural links are checked; this is not a full-range
self-collision proof or verification of omitted motors, cables, or the gripper.

Headless detector verification (empty, distant, overlapping, and removed obstacle):

```bash
ros2 run arctos_collision_demo collision_demo --ros-args \
  -p model:="$HOME/arctos_ws/src/arctos_description/urdf/arctos.urdf" -p verify:=true
```

Reference: [MoveIt Planning Scene](https://moveit.picknik.ai/main/doc/examples/planning_scene/planning_scene_tutorial.html).
