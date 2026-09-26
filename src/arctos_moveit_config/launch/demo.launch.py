from pathlib import Path
import xml.etree.ElementTree as ET

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory('arctos_moveit_config'))
    description = Path(get_package_share_directory('arctos_description'))
    config = share / 'config'
    root = ET.fromstring((description / 'urdf/arctos.urdf').read_text())
    control = ET.SubElement(root, 'ros2_control', name='ArctosMock', type='system')
    hardware = ET.SubElement(control, 'hardware')
    ET.SubElement(hardware, 'plugin').text = 'mock_components/GenericSystem'
    limits = {}
    for joint in root.findall('joint'):
        if joint.get('type') != 'revolute':
            continue
        name = joint.get('name')
        # These speeds and accelerations are demo assumptions, not hardware ratings.
        joint.find('limit').set('velocity', '1.0')
        joint.find('limit').set('effort', '10')
        limits[name] = {'has_velocity_limits': True, 'max_velocity': 1.0,
                        'has_acceleration_limits': True, 'max_acceleration': 1.0}
        controlled = ET.SubElement(control, 'joint', name=name)
        ET.SubElement(controlled, 'command_interface', name='position')
        position = ET.SubElement(controlled, 'state_interface', name='position')
        ET.SubElement(position, 'param', name='initial_value').text = '0.0'
        ET.SubElement(controlled, 'state_interface', name='velocity')
    robot = {'robot_description': ET.tostring(root, encoding='unicode')}
    semantic = {'robot_description_semantic': (config / 'arctos.srdf').read_text()}
    kinematics = {'robot_description_kinematics': yaml.safe_load((config / 'kinematics.yaml').read_text())}
    planning = {'robot_description_planning': {
        'joint_limits': limits,
        'default_velocity_scaling_factor': 1.0,
        'default_acceleration_scaling_factor': 1.0}}
    pipelines = {'planning_pipelines': ['ompl'], 'default_planning_pipeline': 'ompl',
                 'ompl': yaml.safe_load((config / 'ompl_planning.yaml').read_text())}
    controllers = yaml.safe_load((config / 'moveit_controllers.yaml').read_text())
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
