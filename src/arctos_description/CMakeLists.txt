# Require a CMake version supported by this package.
cmake_minimum_required(VERSION 3.8)
# Match the project name to the ROS package manifest.
project(arctos_description)

# Load the ROS build and package registration helpers.
find_package(ament_cmake REQUIRED)

# Install model definitions without copying private mesh assets.
install(DIRECTORY config urdf DESTINATION share/${PROJECT_NAME})
# Include the model preparation instructions in the installed package.
install(FILES README.md DESTINATION share/${PROJECT_NAME})
# Make the mesh preparation script available through ros2 run.
install(PROGRAMS scripts/prepare_meshes.py DESTINATION lib/${PROJECT_NAME})

# Register this package in the ROS environment.
ament_package()
