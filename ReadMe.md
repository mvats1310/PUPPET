# PUPPET — Physical Unified Platform for Presence, Embodiment, and Teleoperation

> **Setup and operating guide — October 2026.** This README explains how PUPPET is put together, how to reproduce its software environment, and how the lab team starts and operates the system. Commands marked **[VERIFY]** still need to be checked against the deployed configuration. Do not use an unverified command, IP address, controller setting, or coordinate transform to move the physical robot. This version is based on the project notes and operator workflow; it has not yet been merged with the README on GitHub.

**PUPPET** is a remote robotics laboratory built around a real PAL Robotics TIAGo robot. A researcher enters a virtual version of the laboratory through a Meta Quest 3 headset and controls the real robot through a Unity interface. ROS handles robot communication, while OptiTrack measures the positions of the robot and the object so that the virtual scene stays aligned with the physical lab. The research task used to test the system is to pick up an object from a table and place it on a shelf. The project also includes scripts for checking and analyzing experimental data.

## Contents

Click a section below to jump directly to it. For a normal lab session, start with **[Section 5](#section-5)** and then follow the **[six-terminal checklist](#section-11)**. If you are installing PUPPET on a new machine, begin with **[Section 4](#section-4)**.


1. [System overview](#section-1)
2. [Hardware and software](#section-2)
3. [Repository layout and authoritative files](#section-3)
4. [Fresh-machine installation](#section-4)
5. [Physical lab and TIAGo preflight — do before any motion](#section-5)
6. [Network and ROS master](#section-6)
7. [Actual laboratory startup: TIAGo, PlayMotion, telepresence, and control](#section-7)
8. [OptiTrack / Motive / NatNet](#section-8)
9. [Coordinate systems, calibration and yaw](#section-9)
10. [Unity virtual laboratory and Meta Quest 3](#section-10)
11. [Daily startup checklist — six terminals](#section-11)
12. [Research outputs (optional, separate from startup)](#section-12)
13. [TIAGo tips and failure prevention](#section-13)
14. [Troubleshooting matrix](#section-14)
15. [Shutdown and recovery](#section-15)


<a id="section-1"></a>

## 1. System overview

```
Researcher / Meta Quest 3
          |
     Unity virtual lab  (MSI workstation)
          |       ^
    ROS–TCP       |  state / RGB / poses
          v       |
    TIAGo ROS master (10.205.3.26)
          |                    ^
    TIAGo controllers          | OptiTrack ROS nodes on archimedes
          |                    |
     Physical TIAGo      Motive / OptiTrack cameras
          |
      Real puck/object, table, shelf

  ROS bags + trial events + metadata + validation + figures
```

**This is a real-robot system, not just a simulation.** When a researcher moves or acts inside PUPPET, the corresponding commands are sent to the physical TIAGo. The robot’s measured state and OptiTrack positions are then sent back to Unity to update the virtual laboratory. For the research study, a trial is only useful if the physical task succeeds **and** the recorded measurements are trustworthy.

**Two flows happen at the same time:** commands move **from Unity or keyboard teleoperation to TIAGo**, while joint states, camera feeds, and OptiTrack measurements move **from the real lab back to Unity**. Seeing the robot move in Unity does not, by itself, prove that the physical robot is accepting commands or that a dataset is being recorded correctly.

<a id="section-2"></a>

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

### Software versions to keep consistent

- ROS Noetic / Ubuntu 20.04 on the mini PC.
- Unity `2022.3.62f2`, Universal Render Pipeline, XR Interaction Toolkit `2.6.5`, OpenXR. Use `Packages/manifest.json` and `packages-lock.json` to recover actual package versions.
- PAL TIAGo controller/URDF configuration matching the deployed gripper and base.
- Rebuild ROS source dependencies from `dependencies/tiago_public_ws.rosinstall` **if that file is present and complete**; confirm uncommitted/local packages separately.
- Python package dependencies must be documented from imports / current environment; do not assume a generic `pip install -r requirements.txt` works unless a pinned file is supplied.

<a id="section-3"></a>

## 3. Repository layout and authoritative files

The repository is organized roughly as follows. Some paths may vary with the Git commit being used:

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

The working mini PC also has a larger ROS workspace at **`~/tiago_public_ws/src`**. It includes PAL Robotics packages and other third-party dependencies that are not necessarily all inside `PUPPET/ros_ws/src`. To recreate the environment, you need **both** the PUPPET-specific source code **and** those external dependencies at the correct versions. Do not upload generated folders (`build/`, `devel/`, `logs/`, Unity `Library/` or `Temp/`), nested `.git` history, or the 88 GB raw dataset to ordinary Git. If a third-party package was changed locally, record that change separately; a dependency manifest alone will not reproduce it.

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

<a id="section-4"></a>

## 4. Fresh-machine installation

### 4.1 Prerequisites and cloning

Start on a Linux computer running **Ubuntu 20.04 and ROS Noetic**, with authorized access to the TIAGo laboratory. Open a terminal and check the operating system, hostname, network connection, and ROS environment:

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

If GitHub asks for authentication, configure an SSH key for the computer. **Cloning PUPPET only downloads the repository:** it does not install the TIAGo software, PAL packages, Motive, or ROS dependencies.

### 4.2 Reconstruct the external ROS source workspace

The mini PC’s working ROS environment is **`~/tiago_public_ws`**. It contains packages such as `tiago_robot`, `tiago_moveit_config`, `play_motion`, `ROS-TCP-Endpoint`, `natnet_ros_cpp`, and `optitrack_ros_communication`. We saved upstream repositories and commit IDs during development. If `dependencies/tiago_public_ws.rosinstall` exists in this checkout and has been checked for completeness, it can serve as a starting point for reconstructing those sources:

```bash
mkdir -p ~/tiago_public_ws/src
cd ~/tiago_public_ws
# [VERIFY] Ensure wstool is installed and the manifest format is valid:
# wstool init src /path/to/PUPPET/dependencies/tiago_public_ws.rosinstall
```

**[VERIFY]** Confirm which workspace tool and dependencies are required (`wstool`, `catkin_tools`, `rosdep`, or PAL-specific repositories), and check for unpublished local changes. **Do not update every repository to its latest version**: that could produce a different system from the one tested.

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

**Use the build method that matches the workspace.** We used `catkin build` during development; `catkin_make` caused problems with some PAL packages. For a new installation, record the catkin profile, dependency versions, and any special compiler flags. `-Werror` was disabled in some development builds, but should only be changed if needed and understood.

The GitHub repository also contains **`PUPPET/ros_ws`**. Before building it, check whether it is intended to be built separately or whether its packages should be used alongside `tiago_public_ws`. These are not automatically interchangeable workspaces.

### 4.4 Unity source and Android build

Open the folder containing `Assets/`, `Packages/`, `ProjectSettings/` (on MSI the working copy was `~/Desktop/pxspatialversion`, copied into `unity/PUPPET_Unity` in Git). Open with Unity `2022.3.62f2`; restore packages; verify the main scene `Assets/MAIN PUPPET SCENE.unity` exists; choose the **actual build scene** from `ProjectSettings/EditorBuildSettings.asset`.

For Quest: use Android build target, OpenXR settings, XR Interaction Toolkit, ARM64 where configured, developer mode/USB authorization, and deploy the built APK. The correct application ID, permissions and build settings must be copied from the project, not guessed. A standalone Linux build or APK is **not** the editable Unity source project.

**Important:** A native NatNet Unity plugin previously caused `DllNotFoundException: NatNetLib` on Quest/Android. Do not require native Windows NatNet binaries to run inside Quest. Use the established Motive → ROS → Unity tracking relay, then verify headset runtime logs.

<a id="section-5"></a>

## 5. Physical lab and TIAGo preflight — do before any motion

**A trained operator must be physically present before TIAGo is enabled.** Make sure the emergency stop is accessible and there is enough clear space for the arm and base. The steps below are a preflight checklist, not a replacement for PAL Robotics safety instructions.

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

<a id="section-6"></a>

## 6. Network and ROS master

PUPPET connects several devices over the lab network: the physical TIAGo, the `archimedes` mini PC, the MSI workstation, Meta Quest 3, and the Motive computer (`gaia`). The following addresses were used during development and in the recorded operating procedure. **Check them against the current network before starting:**

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

For an unfamiliar network, replace the placeholders below with the **actual** ROS master and local machine addresses. This is an example, not a command to paste unchanged:

```bash
export ROS_MASTER_URI=http://<ROS_MASTER_HOST_IP>:11311
export ROS_IP=<THIS_HOST_REACHABLE_IP>
source /opt/ros/noetic/setup.bash
source ~/tiago_public_ws/devel/setup.bash
```

Use `ROS_IP` or `ROS_HOSTNAME` consistently—do not set conflicting addresses. Both sides need to be able to reach each other. If Unity connects from the MSI but the Quest does not, check the network and firewall settings.

Validate:

```bash
rosnode list
rostopic list
rostopic echo -n 1 /joint_states
rostopic hz /joint_states
```

**Confirmed for the supplied lab procedure:** the ROS master URI is `http://10.205.3.26:11311` (the TIAGo-side address in this configuration), the mini PC `archimedes` uses `ROS_IP=10.205.3.122`, and the Motive host uses `10.205.3.3`. Re-check addresses if the network changes. Quest IP and ROS–TCP listener remain to be verified.

Wi-Fi detail from the robot: `wlan0` had Power Management `off`, 5.2 GHz connection, around 200 Mb/s reported link rate, and signal about `-64 dBm` in one measurement. A stable Wi-Fi connection should be checked rather than assuming bandwidth/latency is constant.

<a id="section-7"></a>

## 7. Actual laboratory startup: TIAGo, PlayMotion, telepresence, and control

**This is the startup sequence used in the lab.** Commands for telepresence, PlayMotion, and the `extend` pose are run **on TIAGo** (`pal@tiago-38c`). OptiTrack and the two pose-conversion scripts run **on the `archimedes` mini PC**. The exact physical power-on and emergency-stop release procedures still need to be verified with the lab team. Keep an operator beside the robot and clear its workspace before starting any motion.

### 7.1 Terminal plan

Open **six separate terminals** so that each process can run independently. We label them A–F to make it easy to identify what should be running and where:

| Terminal | Host | Purpose |
|---|---|---|
| A | `archimedes` | OptiTrack/Motive → ROS tracking stream |
| B | TIAGo via SSH | Launch telepresence, and stop/relaunch when necessary |
| C | TIAGo via SSH | Run the `play_motion` node |
| D | TIAGo via SSH | Execute the saved `extend` pose |
| E | `archimedes` | TIAGo base OptiTrack pose → odometry |
| F | `archimedes` | Puck OptiTrack pose → odometry |

For terminals **B, C and D**, connect to the robot using SSH from the mini PC:

```bash
ssh pal@tiago-38c
```

If `tiago-38c` cannot be resolved, use the robot IP confirmed by the lab administrator. **Do not start a second ROS master** to work around an SSH or network problem.

### 7.2 Standard ROS setup on `archimedes`

Every time you open a **new terminal on `archimedes`** for OptiTrack or tracking (A, E, or F), load ROS and point it at the robot’s ROS master:

```bash
source /opt/ros/noetic/setup.bash
source ~/tiago_public_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.205.3.26:11311
export ROS_IP=10.205.3.122
```

Before launching more processes, confirm that the connection to ROS works:

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

These commands load the environment installed **on the physical TIAGo**: PAL **Gallium** and the deployed telepresence package. This is different from the ROS Noetic environment on the mini PC. Confirm that `~/deployed_ws_tele/setup.bash` exists on TIAGo.

### 7.4 Launch telepresence (terminal B)

```bash
roslaunch tiago_telepresence_controllers tiago_real.launch audio:=false tcp_ip:=10.205.3.26
```

This is the actual telepresence launch command used in the lab. It disables audio and uses the recorded `tcp_ip` value. Keep terminal B open while the node runs.

### 7.5 Run PlayMotion (terminal C)

```bash
roslaunch tiago_bringup play_motion.launch arm:=True end_effector:=pal-gripper ft_sensor:=false base_type:=pmb2
```

This starts **PlayMotion**, which allows the operator to request saved robot poses such as `extend`. The options identify the arm, PAL gripper, and `pmb2` base configuration used in this setup.

### 7.6 Move TIAGo to the extended starting pose (terminal D)

```bash
rosrun play_motion run_motion extend
```

**Important startup behavior observed in this lab:** the `extend` pose did not work reliably until telepresence had been started once and then stopped with **Ctrl+C**. After that, launching PlayMotion and running `extend` worked. We have not confirmed *why* this is necessary, so it is recorded as an operator observation rather than a general TIAGo requirement. Always check the controller state and physical clearance before repeating a motion.

**Operator-reported sequence for reaching `extend`:**

1. Source the TIAGo environment and start telepresence in terminal B.
2. Stop that launch using **Ctrl+C**.
3. Start/restart the PlayMotion node in terminal C.
4. Run `rosrun play_motion run_motion extend` from terminal D.
5. Verify the physical arm completed `extend`, with no collision, before beginning VR control.
6. Relaunch telepresence in terminal B when ready to teleoperate, if it was stopped.
7. The operator reports **PlayMotion must be stopped after telepresence launches for normal teleoperated arm motion**, and that **PlayMotion needs restarting when relaunching telepresence**. The exact timing and interaction between the launch files are **[VERIFY]**; this guide does not assert that killing PlayMotion is universally safe. Only stop it using the laboratory's established controlled procedure, once no named motion is in progress.

**Safety note:** Ctrl+C stops a terminal process; it is **not** an emergency stop. Always keep the robot’s emergency-stop button available.

### 7.7 Controller and topic checks

The following interfaces were used during PUPPET development. Check the live ROS graph before assuming every topic is active:

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

Do not run two applications that send competing commands to the arm at the same time.

### 7.8 ROS–TCP Endpoint and 2D control

PUPPET communicates with Unity through ROS–TCP. We used the command below during development, but **it is not yet clear whether it needs a separate terminal** in the final six-terminal setup:

```bash
# [VERIFY whether this is already launched by tiago_real.launch]
roslaunch ros_tcp_endpoint endpoint.launch
```

Before starting another endpoint, check whether the existing launch files already start it. Also confirm the endpoint machine, IP address, and port that Quest uses. Port `10000` appeared in earlier tests but is **not verified as the final value**.

The keyboard condition used `ros_ws/src/keyboard_teleop/scripts/keyboard_arm_teleop.py`. Historical keys: `i/k` forward/back; `j/l` left/right; `w/s` up/down; `+/-` increment; `x` stop; `q` quit. Confirm exact semantics in script before operating the physical arm.

### 7.9 MoveIt / collision notes

If MoveIt reports `START_STATE_IN_COLLISION`, compare the current joint positions against the URDF/SRDF collision model and active controllers. This can happen if the initial configuration does not match the robot or model. **Do not disable collision checks just to make a motion execute.**

<a id="section-8"></a>

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

On `gaia`, open Motive and make sure both rigid bodies are tracked, named correctly, and visible throughout the robot’s workspace. Record the Motive origin, rigid-body IDs, marker layout, and streaming mode. The exact Motive interface steps and unicast/multicast configuration still need **[VERIFY]**.

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

This is the launch command supplied from the working experiment setup. Leave terminal A running during the session.

Inspect streaming:

```bash
rostopic list | grep -E 'natnet|mocap'
rostopic hz /natnet_ros/umh_tiago_base/pose
rostopic echo -n 1 /natnet_ros/umh_tiago_base/pose
rostopic list | grep -E 'object|puck'
```

Use the object topic **actually published in ROS**, not an assumed filename or rigid-body name. If it is missing, check the rigid-body stream in Motive on `gaia` first.

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

<a id="section-9"></a>

## 9. Coordinate systems, calibration and yaw

For PUPPET to feel correct, the real TIAGo and virtual TIAGo must share a consistent position and heading. Motive, ROS, and Unity use their own coordinate frames, so both **position (translation)** and **heading (rotation/yaw)** need to be aligned. A yaw correction cannot fix a wrong coordinate origin.

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

The virtual puck should match the real object. During development, we saw a gap between the gripper and puck and a delay in object following. The intended behavior was for the virtual puck to follow the gripper while grasped and settle into the measured position after release. **[VERIFY]** whether the current project uses mocap alone, parenting, a grasp lock, proxy colliders, or a combination. Also document how lost tracking is handled.

<a id="section-10"></a>

## 10. Unity virtual laboratory and Meta Quest 3

### 10.1 Operator's Quest launch procedure

To use PUPPET without opening Unity Editor, turn on **Meta Quest 3**, open the app library, go to **Unknown Sources**, and launch **`pxspatial`**. The location of Unknown Sources may change after Quest software updates. Make sure the ROS connection, physical TIAGo, and tracking are ready before using controls that move the robot.

### 10.2 Rebuilding the editable virtual environment

The physical laboratory's virtual layout is already included in the GitHub repository's **`unity/` folder**. The MSI source project was built with Unity **2022.3.62f2** and includes `Assets/`, `Packages/`, and `ProjectSettings/`, with the main scene named `Assets/MAIN PUPPET SCENE.unity`.

1. Install the recorded Unity editor version with Android build support.
2. Open the folder containing those three Unity project directories through Unity Hub.
3. Verify the correct scene is enabled in Build Settings.
4. Verify saved XR/OpenXR settings and the runtime network destination in the Unity Inspector (**[VERIFY bridge IP/port]**).
5. Connect and authorize Quest development access, then use **Build and Run** for the Android app.
6. Later, launch the installed `pxspatial` app from Unknown Sources.

The Unity scene contains the virtual lab, but a different physical room still needs to be measured and aligned. Match the real table and shelf, TIAGo reference pose, Motive coordinate origin, and rigid-body setup.

### 10.3 Last-mile tracking alignment

The current operator-reported Unity yaw correction is **approximately −5.0 to −6**. **[VERIFY precise number, units (likely degrees), component and Inspector field.]** Earlier +43.94° and −142.53° values were historical experiments, not the final calibration.

Before enabling robot motion, check that moving the tracked TIAGo and puck produces the expected movements in Unity. The relevant streams are `/odom_mocap` and `/puck_mocap`. A rendered scene alone does not prove the real robot can be controlled safely.

<a id="section-11"></a>

## 11. Daily startup checklist — six terminals

This is the **quick version of the complete startup procedure** in Sections 7–10. It documents the operator’s current workflow, including the PlayMotion behavior described above. Follow the lab’s physical robot safety procedure before any movement.

1. **Physical preflight:** E-stop available, TIAGo powered and approved for motion, space clear, Motive running on `gaia`, Quest charged.
2. **Mini PC terminal A:** source ROS Noetic and `~/tiago_public_ws/devel/setup.bash`, set `ROS_MASTER_URI=http://10.205.3.26:11311` and `ROS_IP=10.205.3.122`, then launch `optitrack_nodes.launch` as shown in §8.3.
3. **TIAGo terminal B:** SSH as `pal`, source Gallium and `~/deployed_ws_tele/setup.bash`, then start `tiago_real.launch` (§7.4).
4. **TIAGo B/C/D to reach `extend`:** operator reports that telepresence must first be interrupted with Ctrl+C, PlayMotion launched in C, and `rosrun play_motion run_motion extend` executed in D. Confirm safe completion. Relaunch telepresence in B and stop PlayMotion only according to the verified controller procedure (§7.4–7.6).
5. **Mini PC terminal E:** start `python3 ~/pose_to_odom.py` with the same ROS environment and network exports.
6. **Mini PC terminal F:** start `python3 ~/puck_pose_to_odom.py` with the same environment.
7. **Verify:** `/joint_states`, `/natnet_ros/umh_tiago_base/pose`, `/odom_mocap`, `/puck_mocap`; resolve current object topic naming before trusting the puck.
8. **Quest:** open Unknown Sources → `pxspatial`; verify real/virtual heading and puck movement before any teleoperated arm motion.

**Note:** The user refers to six operational terminals; ROS–TCP endpoint may be included in an existing launch. Its standalone startup, if needed, still requires confirmation. Do not double-launch controllers or motion nodes.

<a id="section-12"></a>

## 12. Research outputs (optional, separate from startup)

Detailed recording instructions are kept outside this daily startup guide. For research reproducibility, the repository still includes `validation/` scripts and processed reports in `results/summaries/`. The original Mini PC held approximately 88 GB of raw ROS bag data, which was not uploaded to ordinary Git.

The historical validation entry point for a dataset already installed on the Mini PC was:

```bash
cd ~/puppet_quality_layer_v2_consistency_matters
python3 run_validation_pipeline.py --participant P01 --data data
```

**[VERIFY]** Check the participant ID, Python version, and data location for the machine used. `Pipeline finished` does **not** mean every dataset passed validation. Review the trial and curation reports. During development, missing `/tf_static`, duplicated timestamps, and temporary object-tracking jumps affected some derived metrics. Keep the recording and participant-consent procedures in the separate experiment protocol.

<a id="section-13"></a>

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

<a id="section-14"></a>

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

<a id="section-15"></a>

## 15. Shutdown and recovery

After finishing a trial, stop command publication before disconnecting tracking, save/close rosbag and videos, verify recordings, return the robot to a safe supervised pose, release/park the arm through the lab-approved procedure, and then stop launch processes in reverse dependency order. For the laboratory's recorded shutdown procedure, TIAGo should be in its **home pose**, then the operator **long-presses the green power button** and **presses the red emergency-stop button**. **[VERIFY]** Confirm the button sequence against this TIAGo's PAL Robotics shutdown procedure before using it on hardware.

**Unexpected movement or instability:** Press the emergency-stop button, move away from the robot's moving parts, and follow the laboratory's emergency procedure. **Do not try to catch or physically restrain a moving or falling arm**; doing so can cause injury. Arrange the robot's operating area so that people are clear of the arm's possible path.

### Repository and citation

Source repository: <https://github.com/mvats1310/PUPPET>. The project paper's archival citation, license, dataset DOI and publication status should be supplied when finalized. Do not declare unreviewed recordings or participant videos openly downloadable.
