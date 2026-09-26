#!/usr/bin/env python3
"""Apply fixed obstacles, plan to a named SRDF state, validate the path, and optionally execute on mock hardware."""
import argparse
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.qos import DurabilityPolicy, QoSProfile
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Pose
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import CollisionObject, Constraints, JointConstraint, MoveItErrorCodes, RobotState
from moveit_msgs.srv import ApplyPlanningScene, GetMotionPlan, GetStateValidity
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import Header, String

GROUP = 'arm'
LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
# Joint-space tolerances in radians; START matches move_group's allowed_start_tolerance.
SAMPLE_STEP = 0.01
START_TOLERANCE = 0.01
GOAL_TOLERANCE = 0.02
STATE_MAX_AGE_S = 2.0


def lerp(a, b, alpha):
    return [x + alpha * (y - x) for x, y in zip(a, b)]


def contact_pairs(result):
    return [(c.contact_body_1, c.contact_body_2) for c in result.contacts]


class Demo:
    def __init__(self):
        self.node = rclpy.create_node('arctos_plan_blocks')
        self.joints = {}
        self.joints_time = 0.0
        self.mock = None
        self.targets = None
        self.node.create_subscription(JointState, '/joint_states', self.receive_joints, 10)
        self.node.create_subscription(String, '/robot_description', self.receive_model, LATCHED)
        self.node.create_subscription(String, '/robot_description_semantic', self.receive_semantic, LATCHED)
        self.apply = self.client(ApplyPlanningScene, '/apply_planning_scene')
        self.validity = self.client(GetStateValidity, '/check_state_validity')
        self.planner = self.client(GetMotionPlan, '/plan_kinematic_path')

    def receive_joints(self, msg):
        self.joints = {n: p for n, p in zip(msg.name, msg.position) if math.isfinite(p)}
        self.joints_time = time.monotonic()

    def receive_model(self, msg):
        plugins = [item.text for item in ET.fromstring(msg.data).findall('ros2_control/hardware/plugin')]
        self.mock = plugins == ['mock_components/GenericSystem']

    def receive_semantic(self, msg):
        self.targets = {
            state.get('name'): {j.get('name'): float(j.get('value')) for j in state.findall('joint')}
            for state in ET.fromstring(msg.data).findall('group_state') if state.get('group') == GROUP}

    def client(self, kind, name):
        client = self.node.create_client(kind, name)
        if not client.wait_for_service(timeout_sec=60):
            raise RuntimeError(f'Service unavailable: {name}')
        return client

    def wait(self, future, timeout=60):
        rclpy.spin_until_future_complete(self.node, future, timeout_sec=timeout)
        if not future.done() or future.result() is None:
            raise RuntimeError('ROS request failed or timed out')
        return future.result()

    def spin_until(self, ready, timeout):
        deadline = time.monotonic() + timeout
        while not ready() and time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
        return ready()

    def current(self, names):
        if time.monotonic() - self.joints_time > STATE_MAX_AGE_S or any(n not in self.joints for n in names):
            raise RuntimeError('No fresh joint states for the planning group')
        return [self.joints[n] for n in names]

    @staticmethod
    def robot_state(names, values):
        state = RobotState(is_diff=False)
        state.joint_state.name = list(names)
        state.joint_state.position = list(values)
        return state

    def valid(self, names, values):
        request = GetStateValidity.Request(group_name=GROUP, robot_state=self.robot_state(names, values))
        return self.wait(self.validity.call_async(request))

    def add_blocks(self):
        config = Path(get_package_share_directory('arctos_moveit_config')) / 'config/blocks.yaml'
        request = ApplyPlanningScene.Request()
        request.scene.is_diff = True
        request.scene.robot_state.is_diff = True
        for block in yaml.safe_load(config.read_text())['blocks']:
            pose = Pose()
            pose.orientation.w = 1.0
            pose.position.x, pose.position.y, pose.position.z = block['position']
            request.scene.world.collision_objects.append(CollisionObject(
                header=Header(frame_id='base_link'), id=block['name'], operation=CollisionObject.ADD,
                primitives=[SolidPrimitive(type=SolidPrimitive.BOX, dimensions=block['size'])],
                primitive_poses=[pose]))
        if not self.wait(self.apply.call_async(request)).success:
            raise RuntimeError('MoveIt rejected the block scene')
        self.node.get_logger().info('Three fixed blocks applied to the MoveIt planning scene')

    def run(self, target, execute):
        if not self.spin_until(lambda: None not in (self.mock, self.targets) and self.joints, 15):
            raise RuntimeError('Missing robot description, semantic description, or joint states')
        if not self.mock:
            raise RuntimeError('This demo requires mock hardware')
        if target not in self.targets:
            raise RuntimeError(f'Unknown target {target!r}; SRDF states: {sorted(self.targets)}')
        names, goal = list(self.targets[target]), list(self.targets[target].values())
        start = self.current(names)
        self.check_endpoints(names, start, goal)
        trajectory = self.plan(names, start, goal, target)
        self.validate(names, start, trajectory)
        if execute:
            self.execute(names, start, goal, trajectory)

    def check_endpoints(self, names, start, goal):
        for label, values in (('start', start), ('goal', goal)):
            result = self.valid(names, values)
            if not result.valid:
                raise RuntimeError(f'{label} state is invalid: {contact_pairs(result)}')
        # Shows whether a straight joint-space move would collide, i.e. whether a detour is needed.
        hit = None
        for index in range(41):
            result = self.valid(names, lerp(start, goal, index / 40))
            if not result.valid:
                hit = contact_pairs(result)
                break
        self.node.get_logger().info(f'Direct joint interpolation contact: {hit or "none"}')

    def plan(self, names, start, goal, target):
        request = GetMotionPlan.Request()
        motion = request.motion_plan_request
        motion.group_name = GROUP
        motion.pipeline_id = 'ompl'
        motion.planner_id = 'RRTConnectkConfigDefault'
        # Match the RViz budget for the narrow route around the blocks, spent on one search.
        motion.allowed_planning_time = 60.0
        motion.num_planning_attempts = 1
        motion.max_velocity_scaling_factor = 1.0
        motion.max_acceleration_scaling_factor = 1.0
        motion.start_state = self.robot_state(names, start)
        motion.goal_constraints = [Constraints(name=target, joint_constraints=[
            JointConstraint(joint_name=name, position=value, tolerance_above=0.001,
                            tolerance_below=0.001, weight=1.0)
            for name, value in zip(names, goal)])]
        response = self.wait(self.planner.call_async(request), 180).motion_plan_response
        if response.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'Planning failed: MoveIt error {response.error_code.val}')
        if not response.trajectory.joint_trajectory.points:
            raise RuntimeError('Planner returned an empty trajectory')
        return response.trajectory

    def validate(self, names, start, trajectory):
        """Check every timed point and the joint-space segments between them at SAMPLE_STEP."""
        path = trajectory.joint_trajectory
        order = [path.joint_names.index(name) for name in names]
        previous, checked = start, 0
        for point in path.points:
            current = [point.positions[i] for i in order]
            steps = max(1, math.ceil(max(abs(a - b) for a, b in zip(previous, current)) / SAMPLE_STEP))
            for index in range(1, steps + 1):
                if not self.valid(names, lerp(previous, current, index / steps)).valid:
                    raise RuntimeError('Post-planning collision validation failed; execution refused')
            checked += steps
            previous = current
        self.node.get_logger().info(f'Validated {checked} path samples; {len(path.points)} trajectory points')

    def execute(self, names, start, goal, trajectory):
        if max(abs(a - b) for a, b in zip(self.current(names), start)) > START_TOLERANCE:
            raise RuntimeError('Robot moved during planning; replan before executing')
        action = ActionClient(self.node, ExecuteTrajectory, '/execute_trajectory')
        if not action.wait_for_server(timeout_sec=15):
            raise RuntimeError('Execution action unavailable')
        handle = self.wait(action.send_goal_async(ExecuteTrajectory.Goal(trajectory=trajectory)))
        if not handle.accepted:
            raise RuntimeError('Execution rejected')
        duration = Duration.from_msg(trajectory.joint_trajectory.points[-1].time_from_start).nanoseconds * 1e-9
        try:
            result = self.wait(handle.get_result_async(), duration * 2 + 30).result
        except RuntimeError:
            self.wait(handle.cancel_goal_async(), 10)
            raise
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'Execution failed: MoveIt error {result.error_code.val}')
        for _ in range(10):
            rclpy.spin_once(self.node, timeout_sec=0.1)
        error = max(abs(a - b) for a, b in zip(self.current(names), goal))
        if error > GOAL_TOLERANCE:
            raise RuntimeError(f'Final joint error too large: {error:.6f} rad')
        self.node.get_logger().info(f'Mock execution succeeded; maximum goal error {error:.6f} rad')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-only', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--target', default='across_blocks', help='SRDF group_state name')
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    demo = None
    try:
        demo = Demo()
        demo.add_blocks()
        if not args.scene_only:
            demo.run(args.target, args.execute)
    except Exception as error:
        if demo:
            demo.node.get_logger().error(str(error))
        else:
            print(error)
        raise SystemExit(1)
    finally:
        if demo:
            demo.node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
