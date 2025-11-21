cmake_minimum_required(VERSION 3.0)

project(tiago_telepresence_controllers LANGUAGES CXX)

find_package(catkin REQUIRED COMPONENTS
    std_msgs
    geometry_msgs
    controller_interface
    hardware_interface
    pluginlib
    roscpp
    kdl_parser
    urdf
    message_generation
)

find_package(orocos_kdl REQUIRED)

add_message_files(
    FILES
    JointPositions.msg
)

add_service_files(
    FILES
    ArmMotion.srv
)

generate_messages(
    DEPENDENCIES
    std_msgs
)

catkin_package()

include_directories(
    include
    ${catkin_INCLUDE_DIRS}
    ${orocos_kdl_INCLUDE_DIRS}
)

add_library(tiago_st_solvers src/st/MatrixExponential.cpp
                             src/st/ProductOfExponentials.cpp
                             src/st/ScrewTheoryIkProblem.cpp
                             src/st/TiagoSubproblems.cpp
                             src/st/TiagoIkProblem.cpp
                             src/st/ConfigurationSelector.cpp
                             src/st/TiagoConfigurationSelector.cpp
                             src/st/ScrewTheoryTools.cpp
                             src/st/chainiksolverpos_st.cpp
)

target_include_directories(tiago_st_solvers PUBLIC include/st)

target_link_libraries(tiago_st_solvers PUBLIC ${catkin_LIBRARIES})

add_library(${PROJECT_NAME} src/controller_base.cpp
                            src/head_tp_controller.cpp
                            src/torso_tp_controller.cpp
                            src/gripper_tp_controller.cpp
                            src/arm_tp_controller.cpp
                            src/command_buffer.cpp
)

target_link_libraries(${PROJECT_NAME} ${catkin_LIBRARIES})

if(CATKIN_ENABLE_TESTING)
    find_package(rostest REQUIRED)

    add_rostest_gtest(kinematics_test test/kinematics.test test/kinematics.cpp)
    target_link_libraries(kinematics_test ${catkin_LIBRARIES} tiago_st_solvers)

    add_rostest_gtest(kinematics_dual_test test/kinematics_dual.test test/kinematics_dual.cpp)
    target_link_libraries(kinematics_dual_test ${catkin_LIBRARIES} tiago_st_solvers)
endif()

install(TARGETS tiago_st_solvers ${PROJECT_NAME}
    ARCHIVE DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
    LIBRARY DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
    RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY config launch
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(PROGRAMS scripts/tp_controller_switcher.py
                 scripts/arm_motion.py
        DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(FILES tiago_telepresence_controllers_plugins.xml
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
