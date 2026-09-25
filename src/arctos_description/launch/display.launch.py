# Import path helpers for locating installed package files.
import os

# Import the installed-package lookup used for model and config paths.
from ament_index_python.packages import get_package_share_directory
# Import the launch description container.
from launch import LaunchDescription
# Import argument and condition helpers for configurable launches.
from launch.actions import DeclareLaunchArgument
# Import conditions that toggle nodes from a boolean argument.
from launch.conditions import IfCondition, UnlessCondition
# Import substitutions that read launch arguments and file contents.
from launch.substitutions import Command, LaunchConfiguration
# Import the ROS node launch action.
from launch_ros.actions import Node
# Import the parameter wrapper that passes the URDF as a string.
from launch_ros.parameter_descriptions import ParameterValue


# Build the RViz display pipeline for the Arctos description.
def generate_launch_description():
    # Locate this package's installed share directory.
    share_dir = get_package_share_directory('arctos_description')

    # Choose the URDF file to display.
    model_arg = DeclareLaunchArgument(
        'model', default_value=os.path.join(share_dir, 'urdf', 'arctos.urdf'),
        description='Absolute path to the robot URDF file.')
    # Choose the RViz configuration file.
    rviz_config_arg = DeclareLaunchArgument(
        'rviz_config', default_value=os.path.join(share_dir, 'rviz', 'display.rviz'),
        description='Absolute path to the RViz configuration file.')
    # Toggle the joint slider GUI.
    gui_arg = DeclareLaunchArgument(
        'gui', default_value='true',
        description='Start joint_state_publisher_gui when true.')

    # Read the URDF file contents into the robot_description parameter.
    robot_description = ParameterValue(
        Command(['cat ', LaunchConfiguration('model')]), value_type=str)

    # Publish link transforms from the URDF and joint states.
    robot_state_publisher = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}])
    # Publish default joint states when the GUI is disabled.
    joint_state_publisher = Node(
        package='joint_state_publisher', executable='joint_state_publisher',
        condition=UnlessCondition(LaunchConfiguration('gui')))
    # Publish joint states from interactive sliders.
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui', executable='joint_state_publisher_gui',
        condition=IfCondition(LaunchConfiguration('gui')))
    # Display the robot model and transforms in RViz.
    rviz = Node(
        package='rviz2', executable='rviz2',
        arguments=['-d', LaunchConfiguration('rviz_config')])

    # Return the arguments and nodes in launch order.
    return LaunchDescription([
        model_arg, rviz_config_arg, gui_arg,
        robot_state_publisher, joint_state_publisher, joint_state_publisher_gui, rviz,
    ])
