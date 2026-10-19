#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
from trajectory_msgs.msg import JointTrajectory
from moveit_commander import MoveGroupCommander

def pose_cb(msg):
    pose = msg.pose
    group.set_pose_target(pose)
    success, plan, _, _ = group.plan()
    if success and plan.joint_trajectory.points:
        traj = plan.joint_trajectory
        traj.header.stamp = rospy.Time.now()
        pub.publish(traj)
        rospy.loginfo("Published trajectory with %d points", len(traj.points))
    else:
        rospy.logwarn("MoveIt planning failed or empty trajectory.")

if __name__ == '__main__':
    rospy.init_node('vr_to_moveit', anonymous=True)
    rospy.loginfo("Starting VR→MoveIt bridge node...")

    group = MoveGroupCommander("arm_torso")
    pub = rospy.Publisher('/arm_controller/command', JointTrajectory, queue_size=1)
    rospy.Subscriber('/vr_pose', PoseStamped, pose_cb, queue_size=1)

    rospy.loginfo("Listening on /vr_pose, publishing to /arm_controller/command")
    rospy.spin()

