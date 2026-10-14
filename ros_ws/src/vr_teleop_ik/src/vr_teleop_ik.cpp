#include <tf2_eigen/tf2_eigen.h> 
#include <tf2/LinearMath/Transform.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.h>
#include <ros/ros.h>
#include <geometry_msgs/PoseStamped.h>
#include <trajectory_msgs/JointTrajectory.h>
#include <trajectory_msgs/JointTrajectoryPoint.h>
#include <moveit/robot_model_loader/robot_model_loader.h>
#include <moveit/robot_state/robot_state.h>

ros::Publisher traj_pub;
moveit::core::RobotModelPtr model;
moveit::core::RobotStatePtr state;
const moveit::core::JointModelGroup* arm_group;

void poseCallback(const geometry_msgs::PoseStamped::ConstPtr& msg)
{
    state->setToDefaultValues();
    Eigen::Isometry3d target;
    tf2::fromMsg(msg->pose, target);
    bool found_ik = state->setFromIK(arm_group, target);

    if (found_ik)
    {
        std::vector<double> joint_positions;
        state->copyJointGroupPositions(arm_group, joint_positions);

        trajectory_msgs::JointTrajectory traj;
        traj.joint_names = arm_group->getActiveJointModelNames();
        trajectory_msgs::JointTrajectoryPoint point;
        point.positions = joint_positions;
        point.time_from_start = ros::Duration(0.5);
        traj.points.push_back(point);
        traj_pub.publish(traj);
    }
}

int main(int argc, char** argv)
{
    ros::init(argc, argv, "vr_teleop_ik");
    ros::NodeHandle nh;
    traj_pub = nh.advertise<trajectory_msgs::JointTrajectory>("/arm_controller/command", 10);
    ros::Subscriber sub = nh.subscribe("/vr_pose", 10, poseCallback);

    robot_model_loader::RobotModelLoader loader("robot_description");
    model = loader.getModel();
    state.reset(new moveit::core::RobotState(model));
    arm_group = model->getJointModelGroup("arm_torso");

    ros::spin();
    return 0;
}
