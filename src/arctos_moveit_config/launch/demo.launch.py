from pathlib import Path
import xml.etree.ElementTree as ET

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Placeholder effort limit for mock control, not a hardware rating.
MOCK_EFFORT = '10'


def load_yaml(path):
    return yaml.safe_load(path.read_text())


def mock_robot_description(urdf, joint_limits):
    """Add mock ros2_control and the demo velocity limits to the URDF, in memory only."""
    root = ET.fromstring(urdf.read_text())
    control = ET.SubElement(root, 'ros2_control', name='ArctosMock', type='system')
    ET.SubElement(ET.SubElement(control, 'hardware'), 'plugin').text = 'mock_components/GenericSystem'
    for joint in root.findall('joint'):
        if joint.get('type') != 'revolute':
            continue
        name = joint.get('name')
        joint.find('limit').set('velocity', str(joint_limits[name]['max_velocity']))
        joint.find('limit').set('effort', MOCK_EFFORT)
        interfaces = ET.SubElement(control, 'joint', name=name)
        ET.SubElement(interfaces, 'command_interface', name='position')
        position = ET.SubElement(interfaces, 'state_interface', name='position')
        ET.SubElement(position, 'param', name='initial_value').text = '0.0'
        ET.SubElement(interfaces, 'state_interface', name='velocity')
    return ET.tostring(root, encoding='unicode')


def generate_launch_description():
    config = Path(get_package_share_directory('arctos_moveit_config')) / 'config'
    urdf = Path(get_package_share_directory('arctos_description')) / 'urdf/arctos.urdf'
    limits = load_yaml(config / 'joint_limits.yaml')
    robot = {'robot_description': mock_robot_description(urdf, limits['joint_limits'])}
    semantic = {'robot_description_semantic': (config / 'arctos.srdf').read_text()}
    kinematics = {'robot_description_kinematics': load_yaml(config / 'kinematics.yaml')}
    planning = {'robot_description_planning': limits}
    pipelines = {'planning_pipelines': ['ompl'], 'default_planning_pipeline': 'ompl',
                 'ompl': load_yaml(config / 'ompl_planning.yaml')}
    controllers = load_yaml(config / 'moveit_controllers.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true'),
        Node(package='robot_state_publisher', executable='robot_state_publisher', parameters=[robot]),
        Node(package='tf2_ros', executable='static_transform_publisher',
             arguments=['--frame-id', 'world', '--child-frame-id', 'base_link']),
        Node(package='controller_manager', executable='ros2_control_node',
             parameters=[str(config / 'ros2_controllers.yaml')], output='screen'),
        Node(package='controller_manager', executable='spawner',
             arguments=['joint_state_broadcaster', 'arm_controller', '--controller-manager-timeout', '60']),
        Node(package='moveit_ros_move_group', executable='move_group', output='screen',
             parameters=[robot, semantic, kinematics, planning, pipelines, controllers, {
                 'publish_robot_description_semantic': True,
                 'publish_planning_scene': True, 'publish_geometry_updates': True,
                 'publish_state_updates': True, 'publish_transforms_updates': True,
                 'trajectory_execution.allowed_start_tolerance': 0.01}]),
        Node(package='rviz2', executable='rviz2', arguments=['-d', str(config / 'moveit.rviz')],
             parameters=[robot, semantic, kinematics, planning, pipelines],
             condition=IfCondition(LaunchConfiguration('rviz'))),
        Node(package='arctos_moveit_config', executable='plan_blocks.py', arguments=['--scene-only'],
             output='screen'),
    ])
