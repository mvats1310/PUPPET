#!/usr/bin/env python3

import sys
import copy
import termios
import tty
import rospy
import moveit_commander


class KeyboardArmTeleop:
    def __init__(self):
        moveit_commander.roscpp_initialize(sys.argv)
        rospy.init_node("keyboard_arm_teleop_real_safe", anonymous=True)

        self.group = moveit_commander.MoveGroupCommander("arm", wait_for_servers=30.0)

        self.group.set_planning_time(3.0)
        self.group.set_num_planning_attempts(3)

        self.group.set_max_velocity_scaling_factor(0.05)
        self.group.set_max_acceleration_scaling_factor(0.05)

        self.ee_link = self.group.get_end_effector_link()

        self.step = 0.003
        self.busy = False

        print("\n======================================")
        print(" TIAGo REAL Keyboard Arm Teleop")
        print("======================================")
        print("i = hand forward")
        print("k = hand backward")
        print("j = hand left")
        print("l = hand right")
        print("w = hand up")
        print("s = hand down")
        print("+ or = = increase step")
        print("-      = decrease step")
        print("x      = software stop")
        print("q      = quit")
        print("======================================")
        print("Move group  :", self.group.get_name())
        print("End effector:", self.ee_link)
        print("Step        :", self.step, "meters")
        print("Speed       : 5%")
        print("======================================\n")

    def get_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def stop_motion(self):
        self.group.stop()
        self.group.clear_pose_targets()
        rospy.logwarn("SOFTWARE STOP SENT")

    def move_arm(self, dx=0.0, dy=0.0, dz=0.0):
        if self.busy:
            rospy.logwarn("Still executing previous move. Ignoring key.")
            return

        self.busy = True

        try:
            self.group.set_start_state_to_current_state()

            current_pose = self.group.get_current_pose(self.ee_link).pose
            target_pose = copy.deepcopy(current_pose)

            target_pose.position.x += dx
            target_pose.position.y += dy
            target_pose.position.z += dz
            target_pose.orientation = copy.deepcopy(current_pose.orientation)

            self.group.set_pose_target(target_pose, self.ee_link)

            success = self.group.go(wait=True)

            self.group.stop()
            self.group.clear_pose_targets()

            if success:
                rospy.loginfo("Moved dx=%.4f dy=%.4f dz=%.4f", dx, dy, dz)
            else:
                rospy.logwarn("Move failed/skipped by MoveIt.")

            rospy.sleep(0.4)

        except Exception as e:
            rospy.logerr("Move error: %s", str(e))
            self.stop_motion()

        finally:
            self.busy = False

    def run(self):
        while not rospy.is_shutdown():
            key = self.get_key()

            if key == "i":
                self.move_arm(dx=self.step)

            elif key == "k":
                self.move_arm(dx=-self.step)

            elif key == "j":
                self.move_arm(dy=self.step)

            elif key == "l":
                self.move_arm(dy=-self.step)

            elif key == "w":
                self.move_arm(dz=self.step)

            elif key == "s":
                self.move_arm(dz=-self.step)

            elif key == "+" or key == "=":
                self.step = min(0.02, self.step + 0.001)
                rospy.loginfo("Step increased to %.4f m", self.step)

            elif key == "-":
                self.step = max(0.001, self.step - 0.001)
                rospy.loginfo("Step decreased to %.4f m", self.step)

            elif key == "x":
                self.stop_motion()

            elif key == "q":
                print("Exiting.")
                self.stop_motion()
                break


if __name__ == "__main__":
    teleop = None

    try:
        teleop = KeyboardArmTeleop()
        teleop.run()

    except rospy.ROSInterruptException:
        pass

    except KeyboardInterrupt:
        if teleop is not None:
            teleop.stop_motion()

    finally:
        if teleop is not None:
            teleop.stop_motion()
