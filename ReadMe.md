# PUPPET — Physical Unified Platform for Presence, Embodiment, and Teleoperation

> **Reproducibility and operating guide — revised October 2026 draft.** This guide consolidates known details from the PUPPET development record. Items marked **[VERIFY]** are not yet confirmed against the live deployed configuration. Do not operate a physical TIAGo based on an unverified command, address, frame mapping, or controller configuration. This document is a proposed expanded README; it has **not** been merged with the existing GitHub README.

PUPPET is a cyber-physical testbed for remote experimentation with a physical PAL Robotics TIAGo through an immersive virtual laboratory. It combines a Unity-based digital replica, teleoperation through ROS, OptiTrack tracking of the robot and experimental object, live feedback, ROS recordings, and validation of experimental data. The research use case is a table-to-shelf pick-and-place task.

## Contents

1. System overview and architecture
2. Hardware, software and machine responsibilities
3. Repository and ROS workspace structure
4. Reproducing the environment from a fresh machine
5. Physical lab and TIAGo preflight
6. Network and ROS master setup
7. Starting TIAGo and selecting controllers
8. OptiTrack/Motive/NatNet configuration
9. Coordinate frames and yaw alignment
10. Unity and Meta Quest setup
11. Running the end-to-end PUPPET experiment
12. Data collection and validation
13. TIAGo operation notes and known pitfalls
14. Troubleshooting
15. Shutdown and recovery
16. Reproducibility checklist and missing values

## 1. System overview

```
Researcher / Meta Quest 3
          |
     Unity virtual lab  (MSI workstation)
          |       ^
    ROS–TCP       |  state / RGB / poses
          v       |
    ROS master and bridge (archimedes mini PC)
          |                    ^
    MoveIt / teleop             | NatNet/OptiTrack pose topics
          |                    |
     Physical TIAGo      Motive / OptiTrack cameras
          |
      Real puck/object, table, shelf

  ROS bags + trial events + metadata + validation + figures
```

**System components.** The PUPPET interface is not a purely simulated robot. The researcher's actions in the virtual laboratory command the real TIAGo; tracked state and sensor data return to the digital replica. The recorded trial must be both a successful task and a scientifically useful dataset.

**Control vs. synchronization:** control commands travel from the immersive/2D interfaces toward TIAGo; motion capture and robot state return from the real world for visualization and analysis. A correct-looking Unity robot is not proof that TIAGo is receiving commands, nor proof that recording is healthy.

## 2. Hardware and software

| Item | PUPPET reference setup | Notes |
|---|---|---|
| Physical robot | PAL Robotics TIAGo, single arm, PAL gripper | Match URDF and controller configuration to physical robot; never substitute steel gripper parameters blindly |
| Robot onboard computer | TIAGo onboard ROS environment | Hardware-side controller manager; actual startup procedure **[VERIFY]** |
| Mini PC | `archimedes`, Ubuntu 20.04, ROS Noetic | `~/tiago_public_ws`, `~/PUPPET`, validation/recording directories |
| MSI workstation | Unity authoring/development machine | Ubuntu version for current workstation **[VERIFY]**; Unity `2022.3.62f2` URP |
| Headset | Meta Quest 3, OpenXR | Unity XR Interaction Toolkit `2.6.5` per development records |
| Motion capture | OptiTrack cameras, Motive, NatNet ROS bridge | Motive machine/OS, calibration and rigid-body IDs **[VERIFY]** |
| Network | Experiment Wi-Fi 6 AP | Historical SSID `IERobotics-Experiments`, 5.2 GHz; IPs below are historical, not configuration constants |
| Communication | ROS1, ROS–TCP Endpoint/Connector, MoveIt, NatNet | ROS master may be on mini PC or TIAGo; confirm per session |
| Cameras | TIAGo Xtion RGB, side Logitech C270, ceiling USB | External cameras may be recorded using OBS |

### Core software versions to pin

- ROS Noetic / Ubuntu 20.04 on the mini PC.
- Unity `2022.3.62f2`, Universal Render Pipeline, XR Interaction Toolkit `2.6.5`, OpenXR. Use `Packages/manifest.json` and `packages-lock.json` to recover actual package versions.
- PAL TIAGo controller/URDF configuration matching the deployed gripper and base.
- Rebuild ROS source dependencies from `dependencies/tiago_public_ws.rosinstall` **if that file is present and complete**; confirm uncommitted/local packages separately.
- Python package dependencies must be documented from imports / current environment; do not assume a generic `pip install -r requirements.txt` works unless a pinned file is supplied.

## 3. Repository layout and authoritative files

Expected PUPPET layout (some directories depend on the exact Git commit):

```
PUPPET/
  unity/PUPPET_Unity/Assets, Packages, ProjectSettings
  ros_ws/src/tiago_telepresence_controllers/
  ros_ws/src/tiago_vr_bridge/
  ros_ws/src/vr_teleop/
  ros_ws/src/vr_teleop_ik/
  ros_ws/src/keyboard_teleop/
  ros_ws/src/optitrack_ros_communication/
  ros_ws/src/natnet_ros_cpp/           # [VERIFY presence]
  tracking/pose_to_odom.py             # [VERIFY committed]
  tracking/puck_pose_to_odom.py        # [VERIFY committed]
  validation/
  results/summaries/
  dependencies/tiago_public_ws.rosinstall   # [VERIFY committed]
```

On the original mini PC, the more complete PAL/third-party ROS environment was `~/tiago_public_ws/src`, not necessarily `~/PUPPET/ros_ws/src`. A reproducible clone must recover BOTH the custom project packages and the pinned external dependencies. **Do not copy `build/`, `devel/`, `.git` folders nested inside packages, `logs/`, `Library/`, `Temp/`, or 88 GB of raw experiment bags into ordinary Git.** If a dependency was modified locally, a manifest containing only its upstream commit is insufficient; preserve a patch or fork.

Check locally:

```bash
cd ~/PUPPET
git status -sb
git remote -v
find ros_ws/src -name package.xml -not -path '*/.git/*' | sort
find tracking -maxdepth 1 -type f 2>/dev/null
ls dependencies 2>/dev/null
```

To inspect current checkout without altering files:

```bash
git ls-files | grep -E '^(ros_ws/|tracking/|validation/|unity/|dependencies/)'
```

## 4. Fresh-machine installation

### 4.1 Prerequisites and cloning

On an Ubuntu 20.04/ROS Noetic host with authorized access to the physical TIAGo lab:

```bash
lsb_release -a
uname -a
hostname
hostname -I
source /opt/ros/noetic/setup.bash
echo "$ROS_DISTRO"
git clone git@github.com:mvats1310/PUPPET.git
cd PUPPET
```

Set up SSH GitHub authentication separately if needed. Cloning the repository does not install TIAGo drivers, Motive, PAL dependencies, or ROS packages automatically.

### 4.2 Reconstruct the external ROS source workspace

The actual mini PC used `~/tiago_public_ws` with many PAL Robotics and external repositories (`tiago_robot`, `tiago_moveit_config`, `play_motion`, `ROS-TCP-Endpoint`, `natnet_ros_cpp`, `optitrack_ros_communication`, and others). The October 2026 inventory captured individual commit hashes. If the `.rosinstall` manifest was committed and checked for completeness:

```bash
mkdir -p ~/tiago_public_ws/src
cd ~/tiago_public_ws
# [VERIFY] Ensure wstool is installed and the manifest format is valid:
# wstool init src /path/to/PUPPET/dependencies/tiago_public_ws.rosinstall
```

**[VERIFY]** Whether the project uses `wstool`, `catkin_tools`, `rosdep`, and special PAL public-deploy repositories, and whether there are unpublished local changes. Do not run a blanket upgrade against a previously working robot workspace.

The working source directory in the study was `~/tiago_public_ws/src`, size around 445 MB including nested Git metadata. Excluding nested Git histories substantially reduces its apparent size.

### 4.3 Catkin build and sourcing

Known workspace commands from earlier PUPPET development:

```bash
source /opt/ros/noetic/setup.bash
cd ~/tiago_public_ws
catkin build
source devel/setup.bash
rospack find tiago_telepresence_controllers
rospack find ros_tcp_endpoint  # [VERIFY package name for this checkout]
```

**Do not assume `catkin_make` and `catkin build` are interchangeable.** Earlier builds of mixed PAL workspaces failed with `catkin_make`. Record exact dependencies, successful build invocation, profile and compiler flags for a fresh installation. Historical build troubleshooting included disabling `-Werror` **only where needed**.

For the project-specific ROS checkout, there is also `~/PUPPET/ros_ws`; distinguish whether it is a standalone build workspace or a source-only archive before instructing users to build it.

### 4.4 Unity source and Android build

Open the folder containing `Assets/`, `Packages/`, `ProjectSettings/` (on MSI the working copy was `~/Desktop/pxspatialversion`, copied into `unity/PUPPET_Unity` in Git). Open with Unity `2022.3.62f2`; restore packages; verify the main scene `Assets/MAIN PUPPET SCENE.unity` exists; choose the **actual build scene** from `ProjectSettings/EditorBuildSettings.asset`.

For Quest: use Android build target, OpenXR settings, XR Interaction Toolkit, ARM64 where configured, developer mode/USB authorization, and deploy the built APK. The correct application ID, permissions and build settings must be copied from the project, not guessed. A standalone Linux build or APK is **not** the editable Unity source project.

**Important:** A native NatNet Unity plugin previously caused `DllNotFoundException: NatNetLib` on Quest/Android. Do not require native Windows NatNet binaries to run inside Quest. Use the established Motive → ROS → Unity tracking relay, then verify headset runtime logs.

## 5. Physical lab and TIAGo preflight — do before any motion

Only a trained, authorized operator should prepare a physical robot. Maintain a person at the lab with access to emergency stop.

1. Confirm TIAGo is physically stable, clear of personnel, and that table, shelf and tracked object are positioned as in the reference trial; check wheels, arm and gripper clearance.
2. Identify the real robot variant, arm side, base type `pmb2`, single-arm PAL gripper and end-effector model. Confirm no hard-coded `steel_gripper` example is being applied to PAL-gripper hardware.
3. Check E-stop status, collision-free arm starting pose, power/battery/charging state, wired or Wi-Fi connectivity, and which person is supervising. Do not bypass protective stops.
4. Confirm the robot's onboard controller manager is running and the expected hardware controllers appear. The exact physical power-on, unlock and `pal_deploy` procedure **[VERIFY with lab supervisor]**; Gazebo startup commands are not equivalent to real robot startup.
5. Confirm the robot base and OptiTrack tracking reference are not occluded; verify puck marker is rigidly attached in the documented position.
6. Start with no remote motion commands and inspect feedback before enabling VR teleoperation.

### TIAGo operational observations from the project

- The arm sometimes took **5–10 seconds** to initiate after controller activation; this is a historical observation, not a normal guaranteed delay.
- Move slowly, avoid arm overextension and large abrupt poses, and prefer small increments.
- Keep the base and arm away from the shelf until coordinate systems are verified; forward motion was easier for researchers than aggressive lateral moves.
- Gripper open/close control needs to match the actual physical gripper, its control type and ROS topic.
- Start pose mismatch, collision checks, and controller switching can prevent movement even while Unity appears responsive.
- When motion is unexpectedly jerky, stop commanded motion safely; distinguish genuine TIAGo movement from a Unity follower rendering artifact.

## 6. Network and ROS master

The PUPPET experiment had multiple devices: TIAGo, mini PC, MSI, Quest, and Motive/OptiTrack system. Historical addresses **must not be reused without checking the present network**:

| Historical address | Appeared as | Caveat |
|---|---|---|
| `10.205.1.8` | ROS bridge host / mini PC in earlier tests | Historical, may have changed |
| `10.205.3.26` | ROS master URI in operator's procedure | Recheck before use |
| `10.205.3.3` | Motive server on `gaia` | Recheck before use |
| `10.205.3.122` | Mini PC `archimedes` ROS client IP | Confirm with `hostname -I` |
| TCP port `10000` | Historical ROS–TCP Endpoint | Confirm active listener |
| ROS master port `11311` | ROS1 master | Default, unless changed |

On each relevant Linux machine:

```bash
hostname
hostname -I
ip addr
printenv ROS_MASTER_URI
printenv ROS_IP
printenv ROS_HOSTNAME
ping -c 3 <ROS_MASTER_HOST_IP>
```

Set these for the **actual host chosen as ROS master**; examples only:

```bash
export ROS_MASTER_URI=http://<ROS_MASTER_HOST_IP>:11311
export ROS_IP=<THIS_HOST_REACHABLE_IP>
source /opt/ros/noetic/setup.bash
source ~/tiago_public_ws/devel/setup.bash
```

Use `ROS_HOSTNAME` **or** `ROS_IP` consistently rather than setting conflicting values. Confirm name resolution and bidirectional connectivity. Check firewall rules and router isolation if Unity can connect locally but Quest cannot.

Validate:

```bash
rosnode list
rostopic list
rostopic echo -n 1 /joint_states
rostopic hz /joint_states
```

**Confirmed for the supplied lab procedure:** the ROS master URI is `http://10.205.3.26:11311` (the TIAGo-side address in this configuration), the mini PC `archimedes` uses `ROS_IP=10.205.3.122`, and the Motive host uses `10.205.3.3`. Re-check addresses if the network changes. Quest IP and ROS–TCP listener remain to be verified.

Wi-Fi detail from the robot: `wlan0` had Power Management `off`, 5.2 GHz connection, around 200 Mb/s reported link rate, and signal about `-64 dBm` in one measurement. A stable Wi-Fi connection should be checked rather than assuming bandwidth/latency is constant.

## 7. Actual laboratory startup: TIAGo, PlayMotion, telepresence, and control

**This section records the operator's October 2026 working procedure, rather than an inferred generic ROS launch sequence.** The source machine for robot-side commands is **TIAGo** (`pal@tiago-38c`); for NatNet and pose-conversion commands it is **`archimedes`**. The physical power-on/E-stop release and robot's operating-state verification still need to be supplied by the local operator. Keep a trained operator near the real robot and ensure the arm has a clear workspace before triggering any motion.

### 7.1 Terminal plan

Open **six terminal sessions** (the operator's list and terminal numbers were informal; these labels here are normalized):

| Terminal | Host | Purpose |
|---|---|---|
| A | `archimedes` | OptiTrack/Motive → ROS tracking stream |
| B | TIAGo via SSH | Launch telepresence, and stop/relaunch when necessary |
| C | TIAGo via SSH | Run the `play_motion` node |
| D | TIAGo via SSH | Execute the saved `extend` pose |
| E | `archimedes` | TIAGo base OptiTrack pose → odometry |
| F | `archimedes` | Puck OptiTrack pose → odometry |

**SSH into TIAGo from the mini PC** for B, C and D (connection target is known to be `tiago-38c`; verify SSH hostname resolution):

```bash
ssh pal@tiago-38c
```

If that hostname is not resolvable, use the approved robot address provided by your lab administrator; **do not start a new ROS master on the mini PC merely to work around a connection failure**.

### 7.2 Standard ROS setup on `archimedes`

Run this at the start of **each new mini PC terminal** (A, E and F):

```bash
source /opt/ros/noetic/setup.bash
source ~/tiago_public_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.205.3.26:11311
export ROS_IP=10.205.3.122
```

Use the following to verify that the expected robot ROS graph is reachable:

```bash
echo "$ROS_MASTER_URI"
echo "$ROS_IP"
rosnode list
rostopic echo -n 1 /joint_states
```

`10.205.3.122` is the recorded address of `archimedes` for the supplied setup. Use `hostname -I` to verify it before assuming this fixed value works at a different site.

### 7.3 Setup in each TIAGo SSH terminal

In terminals B, C and D after SSH:

```bash
source /opt/pal/gallium/setup.bash
source ~/deployed_ws_tele/setup.bash
```

These two commands matter: the physical TIAGo uses the PAL **Gallium** environment and the **deployed telepresence workspace**, not the mini PC's ROS Noetic `devel` overlay. Check that `~/deployed_ws_tele/setup.bash` is present on the robot before launching.

### 7.4 Launch telepresence (terminal B)

```bash
roslaunch tiago_telepresence_controllers tiago_real.launch audio:=false tcp_ip:=10.205.3.26
```

This is the **user-confirmed physical robot launch command**. `audio:=false` was used; do not silently change the `tcp_ip` parameter.

### 7.5 Run PlayMotion (terminal C)

```bash
roslaunch tiago_bringup play_motion.launch arm:=True end_effector:=pal-gripper ft_sensor:=false base_type:=pmb2
```

This starts the PlayMotion service required to invoke named robot motions. Keep the actual robot hardware configuration (`pal-gripper`, `pmb2`) unchanged.

### 7.6 Move TIAGo to the extended starting pose (terminal D)

```bash
rosrun play_motion run_motion extend
```

**Critical observed quirk:** the experiment operator reports that the `extend` motion only works reliably **after telepresence has first been launched and then interrupted with Ctrl+C**, followed by running the PlayMotion node and calling `run_motion extend`. This is an observation of the present deployment, not a diagnosed requirement of TIAGo or proof of a universal dependency. Do **not** repeatedly trigger the motion without verifying the active robot controllers and clearance.

**Operator-reported sequence for reaching `extend`:**

1. Source the TIAGo environment and start telepresence in terminal B.
2. Stop that launch using **Ctrl+C**.
3. Start/restart the PlayMotion node in terminal C.
4. Run `rosrun play_motion run_motion extend` from terminal D.
5. Verify the physical arm completed `extend`, with no collision, before beginning VR control.
6. Relaunch telepresence in terminal B when ready to teleoperate, if it was stopped.
7. The operator reports **PlayMotion must be stopped after telepresence launches for normal teleoperated arm motion**, and that **PlayMotion needs restarting when relaunching telepresence**. The exact timing and interaction between the launch files are **[VERIFY]**; this guide does not assert that killing PlayMotion is universally safe. Only stop it using the laboratory's established controlled procedure, once no named motion is in progress.

**Do not interpret `Ctrl+C` as an emergency stop**. The robot's physical emergency stop and safety interlocks must remain accessible at all times.

### 7.7 Controller and topic checks

The development interfaces included:

| Interface | ROS message type / meaning |
|---|---|
| `/arm_tp_controller/command` | `geometry_msgs/PoseStamped`, desired arm end-effector pose |
| `/head_tp_controller/command` | `geometry_msgs/QuaternionStamped` |
| `/gripper_tp_controller/command` | `std_msgs/Int32` |
| `/torso_tp_controller/command` | `std_msgs/Int32` |
| `/mobile_base_controller/cmd_vel` | `geometry_msgs/Twist` |
| `/arm_controller` | MoveIt trajectory action where configured |
| `/joint_states` | Joint feedback |
| `/tf`, `/tf_static` | Transforms |
| `/mobile_base_controller/odom` | Robot wheel odometry |
| `/xtion/rgb/image_raw/compressed` | Robot RGB feed |

Check active topic names and controller status on the live graph:

```bash
rostopic list | sort
rostopic type /arm_tp_controller/command
rostopic hz /joint_states
rosservice list | grep controller_manager
```

Do not start multiple competing arm command publishers simultaneously.

### 7.8 ROS–TCP Endpoint and 2D control

PUPPET uses ROS–TCP communication with Unity. The command below appeared in development records but **has not been confirmed as a necessary *separate* terminal in the operator's final six-terminal workflow**:

```bash
# [VERIFY whether this is already launched by tiago_real.launch]
roslaunch ros_tcp_endpoint endpoint.launch
```

Before adding it to startup, inspect the actual `tiago_real.launch` files and running nodes. Determine which host serves the endpoint and which reachable IP/port Quest uses. Historical connection tests used port `10000`; this is **not confirmed as the final runtime setting**.

The keyboard condition used `ros_ws/src/keyboard_teleop/scripts/keyboard_arm_teleop.py`. Historical keys: `i/k` forward/back; `j/l` left/right; `w/s` up/down; `+/-` increment; `x` stop; `q` quit. Confirm exact semantics in script before operating the physical arm.

### 7.9 MoveIt / collision notes

The lab saw `START_STATE_IN_COLLISION` on some motions. Check active controllers, current `joint_states`, URDF/SRDF, and end-effector model before troubleshooting. Never disable collision checking simply to force a trajectory to run.

## 8. OptiTrack / Motive / NatNet

### 8.1 Physical setup

- Calibrate OptiTrack camera volume in Motive and confirm adequate coverage of robot movement and shelf/table.
- Identify rigid bodies for **TIAGo base** and **puck/object**. Development topic names were `/natnet_ros/umh_tiago_base/pose` and `/natnet_ros/umh_object_mahika/pose`. At one stage NatNet produced generic `/natnet_ros/umh_0/pose` through `/umh_9/pose`: names must be inspected, not assumed.
- Attach and document marker positions. The puck marker was mounted toward the top-right in one layout, so marker origin and object center may differ.
- Check Motive streaming settings: server/client IP, multicast vs unicast, rigid body IDs, axis conventions, update rate, and tracking status. **[VERIFY exact settings/screenshots]**.

### 8.2 Motive host, rigid bodies and network

The OptiTrack **Motive machine is `gaia`** in the laboratory. For this known network, the NatNet server IP is `10.205.3.3` and the mini PC client IP is `10.205.3.122`.

The **user-reported Motive rigid-body labels** are:

- TIAGo robot base: `umh_tiago_base`
- Tracked object: `umh_mahika_object`

**Important discrepancy to resolve before publishing:** older code and earlier ROS topic captures refer to `/natnet_ros/umh_object_mahika/pose`, which is *not spelled the same* as the current reported Motive rigid-body name `umh_mahika_object`. Inspect the real topic names and the input topic in `puck_pose_to_odom.py`; never silently assume the names are interchangeable.

Check calibration/streaming in Motive on `gaia`. Document rigid-body IDs, markers, correct orientation, reference origin, streaming mode and whether cameras cover the full task volume. The exact Motive GUI buttons and NatNet unicast/multicast settings are still **[VERIFY]**.

### 8.3 Start OptiTrack ROS bridge (terminal A on `archimedes`)

First, in a **new terminal**:

```bash
source /opt/ros/noetic/setup.bash
source ~/tiago_public_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.205.3.26:11311
export ROS_IP=10.205.3.122
```

Then launch the exact node used by the operator:

```bash
roslaunch optitrack_ros_communication optitrack_nodes.launch serverIP:=10.205.3.3 clientIP:=10.205.3.122
```

This command supersedes the earlier tentative `natnet_client.launch` example. Keep it running while PUPPET is in use.

Inspect streaming:

```bash
rostopic list | grep -E 'natnet|mocap'
rostopic hz /natnet_ros/umh_tiago_base/pose
rostopic echo -n 1 /natnet_ros/umh_tiago_base/pose
rostopic list | grep -E 'object|puck'
```

Use the **actual** object topic returned by `rostopic list` for diagnostics. If the object topic is missing, first check Motive rigid-body streaming and names on `gaia`.

### 8.4 Start base pose-to-odometry bridge (terminal E)

```bash
source /opt/ros/noetic/setup.bash
source ~/tiago_public_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.205.3.26:11311
export ROS_IP=10.205.3.122
python3 ~/pose_to_odom.py
```

Expected development mapping: `/natnet_ros/umh_tiago_base/pose` → `/odom_mocap`, assuming the existing script matches this configuration.

### 8.5 Start object/puck pose-to-odometry bridge (terminal F)

```bash
source /opt/ros/noetic/setup.bash
source ~/tiago_public_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.205.3.26:11311
export ROS_IP=10.205.3.122
python3 ~/puck_pose_to_odom.py
```

Expected development output: `/puck_mocap`. The input topic must be checked against the final `umh_mahika_object` rigid body name.

Validate both conversions:

```bash
rostopic hz /odom_mocap
rostopic echo -n 1 /odom_mocap
rostopic hz /puck_mocap
rostopic echo -n 1 /puck_mocap
```

The two original files were in the Mini PC home directory and were later candidates for `PUPPET/tracking/`. **[VERIFY]** that the exact working copies were committed to the repository; copying a script into GitHub does not alter the executable copy in `~/`.

## 9. Coordinate systems, calibration and yaw

Correct alignment is essential. Frames involved include Motive tracking coordinates, ROS map/odom/base frames, Unity world coordinates and virtual TIAGo/puck transform hierarchy. Track both **rotation** and **translation**; do not compensate for a wrong origin using yaw alone.

### 9.1 Calibration procedure

1. Place the physical TIAGo and puck at documented reference marks; bring robot to a reproducible initial pose.
2. Confirm Motive axes and rigid-body orientation against the physical lab (front of robot, camera reference, horizontal plane).
3. Confirm ROS frame IDs for OptiTrack input/output and use `tf` to inspect transforms.
4. Set the virtual lab's Unity origin, axis convention, scale and floor height; confirm a known forward movement maps to the correct Unity direction.
5. Check robot base yaw, then translation, then puck offsets. Use small nonhazardous movements and inspect the output before full teleoperation.
6. Verify that position remains stable when the robot is stationary and that no excessive smoothing or double-transform is hiding drift.
7. Freeze and document session calibration values with a timestamp and layout version.

### 9.2 Historical Unity yaw values — **not universal defaults**

The **current operator-reported yaw correction is approximately −5.0 to −6** (assumed degrees; **[CONFIRM UNITS AND PRECISE INSPECTOR VALUE]**). Earlier development calibrations of **+43.94°** and **−142.53°** are historical and **not** the final known setting. Do not add them together. The exact component/Inspector field applying the current yaw and the Motive-to-Unity axis mapping remain **[VERIFY]**.

Project follower scripts included `TiagoMocapFollower` and `PuckMocapFollower`, with smoothing, lock-height behavior, configurable yaw offset, and example motion parameters `catchUpDistance = 0.005`, `catchUpSpeed = 150`. Confirm current values in the exact committed C# scripts/prefabs (serialized Inspector values may differ from script defaults). An inverted yaw or mirror mapping can make a forward physical motion appear backward in Unity.

### 9.3 Puck grasping

The puck should represent the physical tracked object, not be arbitrarily attached to the robot at all times. Historical visual discrepancy: gripper/puck gap, delayed follow, and a request that the virtual object follow the gripper while grasped and then settle at open/release. **[VERIFY]** Which final implementation is present: mocap-only update, gripper-parenting, grasp lock, proxy collider, or hybrid synchronization. Document behavior on lost tracking and actual gripper open.

## 10. Unity virtual laboratory and Meta Quest 3

### 10.1 Operator's Quest launch procedure

The actual PUPPET experiment uses a **Meta Quest 3 APK**. In the headset application library, go to **Unknown Sources** and open the app named **`pxspatial`**. (The menu location may change between Quest OS releases.) Ensure the ROS tracking and robot are operational and the physical operator is supervising before trying any arm movements.

### 10.2 Rebuilding the editable virtual environment

The physical laboratory's virtual layout is already included in the GitHub repository's **`unity/` folder**. The MSI source project was built with Unity **2022.3.62f2** and includes `Assets/`, `Packages/`, and `ProjectSettings/`, with the main scene named `Assets/MAIN PUPPET SCENE.unity`.

1. Install the recorded Unity editor version with Android build support.
2. Open the folder containing those three Unity project directories through Unity Hub.
3. Verify the correct scene is enabled in Build Settings.
4. Verify saved XR/OpenXR settings and the runtime network destination in the Unity Inspector (**[VERIFY bridge IP/port]**).
5. Connect and authorize Quest development access, then use **Build and Run** for the Android app.
6. Later, launch the installed `pxspatial` app from Unknown Sources.

The virtual scene does not automatically calibrate a *new physical room*: match real table/shelf positions, robot pose, Motive origin and rigid bodies.

### 10.3 Last-mile tracking alignment

The current operator-reported Unity yaw correction is **approximately −5.0 to −6**. **[VERIFY precise number, units (likely degrees), component and Inspector field.]** Earlier +43.94° and −142.53° values were historical experiments, not the final calibration.

Before permitting motion, check that the virtual TIAGo responds consistently to real base tracking (`/odom_mocap`) and that the puck responds to `/puck_mocap`. Unity rendering alone does not confirm the robot is safely controllable.

## 11. Daily startup checklist — six terminals

Use this order as a **record of the operator's current workflow**, with the PlayMotion quirk documented explicitly. Physical robot startup/E-stop remains governed by the laboratory's safety procedure.

1. **Physical preflight:** E-stop available, TIAGo powered and approved for motion, space clear, Motive running on `gaia`, Quest charged.
2. **Mini PC terminal A:** source ROS Noetic and `~/tiago_public_ws/devel/setup.bash`, set `ROS_MASTER_URI=http://10.205.3.26:11311` and `ROS_IP=10.205.3.122`, then launch `optitrack_nodes.launch` as shown in §8.3.
3. **TIAGo terminal B:** SSH as `pal`, source Gallium and `~/deployed_ws_tele/setup.bash`, then start `tiago_real.launch` (§7.4).
4. **TIAGo B/C/D to reach `extend`:** operator reports that telepresence must first be interrupted with Ctrl+C, PlayMotion launched in C, and `rosrun play_motion run_motion extend` executed in D. Confirm safe completion. Relaunch telepresence in B and stop PlayMotion only according to the verified controller procedure (§7.4–7.6).
5. **Mini PC terminal E:** start `python3 ~/pose_to_odom.py` with the same ROS environment and network exports.
6. **Mini PC terminal F:** start `python3 ~/puck_pose_to_odom.py` with the same environment.
7. **Verify:** `/joint_states`, `/natnet_ros/umh_tiago_base/pose`, `/odom_mocap`, `/puck_mocap`; resolve current object topic naming before trusting the puck.
8. **Quest:** open Unknown Sources → `pxspatial`; verify real/virtual heading and puck movement before any teleoperated arm motion.

**Note:** The user refers to six operational terminals; ROS–TCP endpoint may be included in an existing launch. Its standalone startup, if needed, still requires confirmation. Do not double-launch controllers or motion nodes.

## 12. Research outputs (optional, separate from startup)

The operator requested that experimental recording instructions **not** be part of the main startup procedure. The repository does include `validation/` scripts and published `results/summaries/` for reproducing analysis. Raw participant rosbags (about 88 GB on the original Mini PC) were excluded from ordinary Git.

The historical validation entry point for a dataset already installed on the Mini PC was:

```bash
cd ~/puppet_quality_layer_v2_consistency_matters
python3 run_validation_pipeline.py --participant P01 --data data
```

**[VERIFY]** The actual participant ID, Python executable and presence of the dataset before running. A finished pipeline does not guarantee every step passed: review the curation/validation reports. Known metrics caveats included missing `/tf_static` in some bags, large numerical jerk from repeated timestamps, and stale/jumping OptiTrack object poses. Detailed trial-recording/video procedures can be documented separately if shared with research participants or reproduction teams.

## 13. TIAGo tips and failure prevention

- **Robot version matters:** matches `pmb2` base, end effector and arm controller loaded on physical TIAGo.
- **ROS master ownership matters:** `roscore` on the wrong machine can create an isolated graph that appears healthy locally but cannot control robot hardware.
- **Controller ownership matters:** command topics may accept messages even if no active controller consumes them.
- **MoveIt collision checking matters:** inspect actual URDF/SRDF and current state when `START_STATE_IN_COLLISION` occurs; do not disable collision checks just to move.
- **Joint-state feedback matters:** a frozen `/joint_states` can cause robot-virtual mismatch and invalid trajectories.
- **Rigid body names matter:** NatNet generic `/umh_0` numbering may change across Motive sessions.
- **Yaw is session-specific:** historic `+43.94°` and `−142.53°` aren't globally valid.
- **Safety and occlusion matter:** object marker offsets and shelf visibility affect apparent grasp success.
- **Network stability matters:** verify TIAGo Wi-Fi power management and signal; `iwconfig wlan0` showed `Power Management:off` in one experiment.
- **A Unity pose is not a measured physical pose:** clarify whether displayed position comes from wheel odometry, joint states, OptiTrack or predicted follower interpolation.

## 14. Troubleshooting matrix

| Symptom | Check first | Do not assume |
|---|---|---|
| Unity ROS connection refused | ROS–TCP endpoint running, IP/port, network reachability | This is an OptiTrack fault |
| `/joint_states` absent | ROS master URI, robot bringup, active hardware | Unity scene is the root cause |
| MoveIt aborts `START_STATE_IN_COLLISION` | Current state/URDF/SRDF, gripper model, self-collision | A controller is broken |
| TIAGo does not move after VR input | Command topic type/rate, controller switcher and active controllers, limits | Delay means movement will eventually happen |
| Robot in Unity mirrored or yaw-offset | Coordinate handedness, parent transform, active yaw offset, origin | One hard-coded yaw fixes every room layout |
| Puck doesn't follow or teleports | NatNet rigid body, stale timestamps, marker offsets, grasp logic | Tracking is always correct |
| Motive connects but no useful ROS topics | Server/client IP, unicast/multicast, rigid-body streaming and names | `/umh_tiago_base/pose` always exists |
| ROS bag present but unusable | `rosbag info`, timestamps, `/tf_static`, events/metadata completeness | File existence means data validity |
| Quest APK fails `NatNetLib` | Native plugin platform support; use ROS relay | Windows native library works on Android |
| Catkin build fails | Source overlay, dependencies, package versions, `catkin build` vs `catkin_make` | Update every upstream repository |
| SSH/GitHub push fails | `ssh -T git@github.com`, SSH key permissions, exact `origin` URL | A robot/network issue |

## 15. Shutdown and recovery

After finishing a trial, stop command publication before disconnecting tracking, save/close rosbag and videos, verify recordings, return the robot to a safe supervised pose, release/park the arm through the lab-approved procedure, and then stop launch processes in reverse dependency order. **[VERIFY]** Exact TIAGo arm stow and power-off commands. Do not kill core robot controllers blindly while the robot is moving.

On unexpected physical movement: follow the local emergency stop procedure immediately. A ROS `x` stop or Ctrl-C of a script is not a substitute for a hardware emergency stop.

## 16. Reproducibility checklist and required verification

Before marking the README **tested end-to-end**, capture:

- [ ] Actual original GitHub README and reconcile with this guide; preserve existing citations and licensing.
- [ ] Exact real TIAGo startup / deployment / unlock / motion commands; full screen or logs from a successful run.
- [ ] ROS master machine, static/dynamic IP addressing, bridge endpoint port and firewall notes.
- [ ] Current Motive streaming settings and rigid body IDs/names; screenshot of calibration origin/axes.
- [ ] Exact launch commands for `natnet_client.launch`, ROS–TCP, controller switcher and MoveIt.
- [ ] Compare committed tracking scripts to working copies in `/home/mahika/`, including object rigid-body naming (`umh_mahika_object` versus `umh_object_mahika`).
- [ ] Confirm the precise current yaw correction (reported around −5 to −6), its units, Inspector field and scene hierarchy.
- [ ] Exact valid initial robot, torso, head, arm and gripper poses; which are safe for physical hardware.
- [ ] Required OS/apt/Python dependencies and pinned ROS source manifest, including uncommitted modifications.
- [ ] Experimental reset and task scoring instructions; participant practice/session procedure.
- [ ] Keep detailed experiment recording protocol separate; document dataset release permissions before publication.
- [ ] Test a clone on a clean machine, replay a representative bag, and perform a supervised live trial.

### Repository and citation

Source repository: <https://github.com/mvats1310/PUPPET>. The project paper's archival citation, license, dataset DOI and publication status should be supplied when finalized. Do not declare unreviewed recordings or participant videos openly downloadable.
