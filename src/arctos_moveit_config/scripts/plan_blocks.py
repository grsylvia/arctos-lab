#!/usr/bin/env python3
"""Apply fixed obstacles, verify a MoveIt path, and optionally execute on mock hardware."""
import argparse
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import rclpy
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, DurabilityPolicy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Pose
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import CollisionObject, Constraints, JointConstraint, RobotState
from moveit_msgs.srv import ApplyPlanningScene, GetMotionPlan, GetPositionFK, GetStateValidity
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import String

from tool_path_plot import plot_tool_path

NAMES = [f'joint_{i}' for i in range(1, 7)]


class Demo:
    def __init__(self):
        self.node = rclpy.create_node('arctos_plan_blocks')
        self.positions = None
        self.state_time = 0.0
        self.mock = False
        self.node.create_subscription(JointState, '/joint_states', self.receive_state, 10)
        self.node.create_subscription(String, '/robot_description', self.receive_model,
                                      QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.apply = self.client(ApplyPlanningScene, '/apply_planning_scene')
        self.validity = self.client(GetStateValidity, '/check_state_validity')
        self.planner = self.client(GetMotionPlan, '/plan_kinematic_path')

    def receive_state(self, msg):
        values = dict(zip(msg.name, msg.position))
        if all(name in values and math.isfinite(values[name]) for name in NAMES):
            self.positions = [values[name] for name in NAMES]
            self.state_time = time.monotonic()

    def receive_model(self, msg):
        root = ET.fromstring(msg.data)
        plugins = [item.text for item in root.findall('ros2_control/hardware/plugin')]
        self.mock = plugins == ['mock_components/GenericSystem']

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

    def robot_state(self, values):
        result = RobotState()
        result.joint_state.name = NAMES
        result.joint_state.position = list(values)
        result.is_diff = False
        return result

    def valid(self, values):
        request = GetStateValidity.Request()
        request.group_name = 'arm'
        request.robot_state = self.robot_state(values)
        return self.wait(self.validity.call_async(request))

    def add_blocks(self):
        config = Path(get_package_share_directory('arctos_moveit_config')) / 'config/blocks.yaml'
        request = ApplyPlanningScene.Request()
        request.scene.is_diff = True
        request.scene.robot_state.is_diff = True
        self.blocks = yaml.safe_load(config.read_text())['blocks']
        for block in self.blocks:
            obstacle = CollisionObject()
            obstacle.header.frame_id = 'base_link'
            obstacle.id = block['name']
            obstacle.operation = CollisionObject.ADD
            obstacle.primitives = [SolidPrimitive(type=SolidPrimitive.BOX, dimensions=block['size'])]
            pose = Pose()
            pose.orientation.w = 1.0
            pose.position.x, pose.position.y, pose.position.z = block['position']
            obstacle.primitive_poses = [pose]
            request.scene.world.collision_objects.append(obstacle)
        if not self.wait(self.apply.call_async(request)).success:
            raise RuntimeError('MoveIt rejected the block scene')
        self.node.get_logger().info('Three fixed blocks applied to the MoveIt planning scene')

    def tool_path(self, samples):
        fk = self.client(GetPositionFK, '/compute_fk')
        path = []
        for values in samples:
            request = GetPositionFK.Request()
            request.header.frame_id = 'base_link'
            request.fk_link_names = ['tool0']
            request.robot_state = self.robot_state(values)
            response = self.wait(fk.call_async(request))
            if response.error_code.val != 1:
                raise RuntimeError(f'FK failed: MoveIt error {response.error_code.val}')
            point = response.pose_stamped[0].pose.position
            path.append((point.x, point.y, point.z))
        return path

    def run(self, execute, target, plot):
        deadline = time.monotonic() + 15
        while (self.positions is None or not self.mock) and time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
        if not self.mock or self.positions is None or time.monotonic() - self.state_time > 2:
            raise RuntimeError('This demo requires mock hardware and fresh joint states')
        start = list(self.positions)
        goal = [1.0 if target == 'across_blocks' else 0.0, 0., 0., 0., 0., 0.]
        for name, values in [('start', start), ('goal', goal)]:
            result = self.valid(values)
            if not result.valid:
                pairs = [(c.contact_body_1, c.contact_body_2) for c in result.contacts]
                raise RuntimeError(f'{name} state is invalid: {pairs}')
        direct_hit = None
        for index in range(41):
            alpha = index / 40
            values = [a + alpha * (b - a) for a, b in zip(start, goal)]
            result = self.valid(values)
            if not result.valid:
                direct_hit = [(c.contact_body_1, c.contact_body_2) for c in result.contacts]
                break
        self.node.get_logger().info(f'Direct joint interpolation contact: {direct_hit or "none"}')
        request = GetMotionPlan.Request()
        motion = request.motion_plan_request
        motion.group_name = 'arm'
        motion.pipeline_id = 'ompl'
        motion.planner_id = 'RRTConnectkConfigDefault'
        # Match the RViz budget for the narrow route around the blocks.
        motion.allowed_planning_time = 60.0
        # Spend the budget on one search.
        motion.num_planning_attempts = 1
        motion.max_velocity_scaling_factor = 1.0
        motion.max_acceleration_scaling_factor = 1.0
        motion.start_state = self.robot_state(start)
        constraints = Constraints(name=target)
        constraints.joint_constraints = [
            JointConstraint(joint_name=name, position=value, tolerance_above=0.001,
                            tolerance_below=0.001, weight=1.0)
            for name, value in zip(NAMES, goal)]
        motion.goal_constraints = [constraints]
        response = self.wait(self.planner.call_async(request), 180).motion_plan_response
        if response.error_code.val != 1:
            raise RuntimeError(f'Planning failed: MoveIt error {response.error_code.val}')
        trajectory = response.trajectory
        points = trajectory.joint_trajectory.points
        if not points:
            raise RuntimeError('Planner returned an empty trajectory')
        order = [trajectory.joint_trajectory.joint_names.index(name) for name in NAMES]
        previous = start
        samples = [start]
        # Check the timed output as well as its interpolated segments at <= 0.01 rad increments.
        for point in points:
            current = [point.positions[i] for i in order]
            steps = max(1, math.ceil(max(abs(a-b) for a, b in zip(previous, current)) / 0.01))
            for index in range(1, steps + 1):
                alpha = index / steps
                values = [a + alpha * (b-a) for a, b in zip(previous, current)]
                if not self.valid(values).valid:
                    raise RuntimeError('Post-planning collision validation failed; execution refused')
                samples.append(values)
            previous = current
        self.node.get_logger().info(
            f'Validated {len(samples) - 1} path samples; {len(points)} trajectory points')
        if plot:
            plot_tool_path(self.tool_path(samples), self.blocks, plot, f'tool0 path to {target}')
            self.node.get_logger().info(f'Tool path plot saved to {plot}')
        if not execute:
            return
        if max(abs(a-b) for a, b in zip(self.positions, start)) > 0.01:
            raise RuntimeError('Robot moved during planning; replan before executing')
        action = ActionClient(self.node, ExecuteTrajectory, '/execute_trajectory')
        if not action.wait_for_server(timeout_sec=15):
            raise RuntimeError('Execution action unavailable')
        handle = self.wait(action.send_goal_async(ExecuteTrajectory.Goal(trajectory=trajectory)))
        if not handle.accepted:
            raise RuntimeError('Execution rejected')
        duration = points[-1].time_from_start.sec + points[-1].time_from_start.nanosec * 1e-9
        result_future = handle.get_result_async()
        try:
            result = self.wait(result_future, duration * 2 + 30).result
        except RuntimeError:
            self.wait(handle.cancel_goal_async(), 10)
            raise
        if result.error_code.val != 1:
            raise RuntimeError(f'Execution failed: MoveIt error {result.error_code.val}')
        for _ in range(10):
            rclpy.spin_once(self.node, timeout_sec=0.1)
        error = max(abs(a-b) for a, b in zip(self.positions, goal))
        if error > 0.02:
            raise RuntimeError(f'Final joint error too large: {error:.6f} rad')
        self.node.get_logger().info(f'Mock execution succeeded; maximum goal error {error:.6f} rad')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-only', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--target', choices=['home', 'across_blocks'], default='across_blocks')
    parser.add_argument('--plot', metavar='PNG', help='save a 3D tool0 path plot to this file')
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    demo = None
    try:
        demo = Demo()
        demo.add_blocks()
        if not args.scene_only:
            demo.run(args.execute, args.target, args.plot)
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
