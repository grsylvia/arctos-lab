cmake_minimum_required(VERSION 3.8)
project(arctos_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch rviz urdf DESTINATION share/${PROJECT_NAME})
install(FILES README.md DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/prepare_meshes.py scripts/prepare_collision_meshes.py scripts/joint_limits.py
        DESTINATION lib/${PROJECT_NAME})

# Private meshes are generated under the Git-ignored cad/ directory and installed locally only.
set(ARCTOS_CAD_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../cad/2.9.7")
install(DIRECTORY "${ARCTOS_CAD_DIR}/urdf_meshes/" DESTINATION share/${PROJECT_NAME}/meshes
        FILES_MATCHING PATTERN "*.stl")
install(DIRECTORY "${ARCTOS_CAD_DIR}/collision_meshes/" DESTINATION share/${PROJECT_NAME}/meshes/collision
        FILES_MATCHING PATTERN "*.stl")

ament_package()
