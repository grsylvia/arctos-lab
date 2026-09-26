from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    description = Path(get_package_share_directory('arctos_description'))
    demo = Path(get_package_share_directory('arctos_collision_demo'))
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(description / 'launch/display.launch.py')),
            launch_arguments={'rviz_config': str(demo / 'launch/collision.rviz')}.items()),
        Node(package='arctos_collision_demo', executable='collision_demo',
             output='screen', parameters=[{
                 'model': str(description / 'urdf/arctos.urdf')}]),
    ])
