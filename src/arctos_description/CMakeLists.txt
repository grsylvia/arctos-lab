# Require a CMake version supported by this package.
cmake_minimum_required(VERSION 3.8)
# Match the project name to the ROS package manifest.
project(arctos_description)

# Load the ROS build and package registration helpers.
find_package(ament_cmake REQUIRED)

# Install the model definitions where ROS tools can find them.
install(DIRECTORY config urdf DESTINATION share/${PROJECT_NAME})
# Locate the private link meshes exported under the Git-ignored CAD directory.
set(ARCTOS_MESH_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../cad/2.9.7/urdf_meshes")
# Copy only the private link STLs into the local install space.
install(DIRECTORY "${ARCTOS_MESH_DIR}/" DESTINATION share/${PROJECT_NAME}/meshes FILES_MATCHING PATTERN "*.stl")
# Include the model preparation instructions in the installed package.
install(FILES README.md DESTINATION share/${PROJECT_NAME})
# Make the mesh preparation script available through ros2 run.
install(PROGRAMS scripts/prepare_meshes.py DESTINATION lib/${PROJECT_NAME})
# Install the RViz launch file and display configuration.
install(DIRECTORY launch rviz DESTINATION share/${PROJECT_NAME})

# Register this package in the ROS environment.
ament_package()
