cmake_minimum_required(VERSION 3.0.2)
project(vr_teleop_ik)

## Find catkin and any catkin packages
find_package(catkin REQUIRED COMPONENTS
  roscpp
  geometry_msgs
  trajectory_msgs
  moveit_core
  moveit_ros_planning
  tf2
  tf2_eigen
  tf2_geometry_msgs
)

## Declare catkin package
catkin_package()

## Include directories
include_directories(
  ${catkin_INCLUDE_DIRS}
)

## Build the C++ node
add_executable(${PROJECT_NAME}_node src/vr_teleop_ik.cpp)
target_link_libraries(${PROJECT_NAME}_node ${catkin_LIBRARIES})
