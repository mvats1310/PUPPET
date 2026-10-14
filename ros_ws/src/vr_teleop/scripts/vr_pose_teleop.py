#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
from moveit_commander import MoveGroupCommander, roscpp_initialize

def callback(msg):
    try:
        arm.set_pose_reference_frame("base_link")
        arm.set_max_velocity_scaling_factor(0.1)
        arm.set_max_acceleration_scaling_factor(0.1)

        arm.set_pose_target(msg.pose)
        plan = arm.plan()

        if plan and plan.joint_trajectory.points:
            rospy.loginfo("Executing plan to new VR pose...")
            arm.execute(plan, wait=True)
        else:
            rospy.logwarn("No valid plan found. Clearing targets and retrying.")
            arm.clear_pose_targets()

    except Exception as e:
        rospy.logerr(f"VR teleop error: {e}")

if __name__ == "__main__":
    roscpp_initialize([])
    rospy.init_node("vr_pose_teleop")
    arm = MoveGroupCommander("arm_torso")

    rospy.loginfo("VR teleop node started — listening to /vr_pose")
    rospy.Subscriber("/vr_pose", PoseStamped, callback, queue_size=1)
    rospy.spin()
