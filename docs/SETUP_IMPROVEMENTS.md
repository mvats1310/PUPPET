# PUPPET setup improvements (branch `lab-demo`)

This branch replaces the six-terminal startup with a single command on the `archimedes` mini PC. It also fixes several problems that stop a fresh machine from reproducing the setup. It was first run on the physical TIAGo on 2026-10-26; see [First hardware session](#first-hardware-session-2026-10-26).

## 1. The one-command session

```bash
# on archimedes, from the PUPPET checkout
./puppet doctor     # preflight: IPs, ping, SSH, ROS master, already-running nodes
./puppet up         # whole startup, in the lab's order, inside a tmux session
./puppet check      # health of a running session
./puppet reset-arm  # back to 'extend' and restart telepresence, without restarting mocap
./puppet down       # stop everything in reverse order
```

`./puppet up` runs the same commands as Sections 7–8 and 11 of the ReadMe. Every long-running process still gets its own window with its own log, now as tmux windows instead of separate terminals:

| Before (ReadMe §11) | Now |
|---|---|
| A: `optitrack_nodes.launch` on archimedes | window `mocap`: `roslaunch puppet_bringup mocap.launch` |
| E: `python3 ~/pose_to_odom.py` | in the same launch file |
| F: `python3 ~/puck_pose_to_odom.py` | in the same launch file |
| B: SSH, source Gallium, `tiago_real.launch` | window `telepresence` (SSH started by the script) |
| C: SSH, source Gallium, `play_motion.launch` | window `play_motion` (SSH started by the script) |
| D: SSH, `rosrun play_motion run_motion extend` | run by the script after the operator confirms |
| Start telepresence, Ctrl+C, then PlayMotion | handled automatically (see §2) |
| Exports typed into every terminal | `config/puppet.env`, loaded once |

The sequence `up` follows:

1. Preflight (`doctor`), then asks the operator to confirm the physical preflight (ReadMe §5).
2. Starts the mocap launch and waits for `/natnet_ros/umh_tiago_base/pose` and `/odom_mocap`.
3. Loads the `extend` definition on TIAGo (see §2).
4. Runs the start-telepresence-then-Ctrl+C workaround **only if** `arm_controller` or `torso_controller` is not running.
5. Starts PlayMotion and waits for its action server. If a `/play_motion` node is already running, that one is reused.
6. **Asks the operator before the arm moves**, runs `extend`, then asks whether it finished cleanly.
7. Starts telepresence and waits until `arm_tp_controller` is running and the ROS-TCP port answers.
8. Stops PlayMotion, as in the operator's procedure (`STOP_PLAY_MOTION_AFTER_TELEPRESENCE`).
9. Runs `check`, then attaches to tmux. The final step is still Quest → Unknown Sources → `pxspatial`.

`./puppet down` stops telepresence first, so command publication ends before tracking stops. Then PlayMotion, then mocap.

All addresses, names and paths live in [`config/puppet.env`](../config/puppet.env). Overrides for one machine or one session go in `config/puppet.local.env`, which is git-ignored. For example, if `check` shows the puck under a different name:

```bash
echo 'PUCK_TOPIC=/natnet_ros/umh_mahika_object/pose' >> config/puppet.local.env
```

Notes on the design:

- **tmux, not one big roslaunch.** The work spans two machines and two ROS environments: Noetic on archimedes, PAL Gallium in `~/deployed_ws_tele` on TIAGo. One roslaunch with `<machine>` tags would require redeploying to the robot and SSH host keys in paramiko's format. It would also take down every process if one side dropped. tmux keeps the familiar one-log-per-process view and needs no change on the robot.
- **Nothing on TIAGo has to change.** The script runs the same `roslaunch`/`rosrun` commands over SSH that the operator types today. It uses one shared SSH connection (`ControlMaster`), so a password is asked at most once. `ssh-copy-id pal@tiago-38c` removes even that.
- **It never starts a ROS master.** `doctor` fails if TIAGo's master is unreachable, and the mocap launch uses `roslaunch --wait`.
- **Motion is always gated by the operator.** `--yes` skips the prompts and is meant only for an operator who has already checked the area.

## 2. Why the "start telepresence, Ctrl+C, then PlayMotion" step was needed (likely)

The `extend` pose is not a stock PAL motion. It is defined in `ros_ws/src/tiago_telepresence_controllers/config/telepresence_motions.yaml` (with PUPPET's own joint values, which differ from upstream). The only thing that loads that file is `telepresence_controllers.launch`, through `tiago_real.launch`. So before telepresence has run once, `/play_motion/motions/extend` is missing from the parameter server and `run_motion extend` has nothing to play. ROS parameters survive Ctrl+C, so after the first start/stop it works. That matches what the operator saw.

There is a second possible cause. On Ctrl+C, `tp_controller_switcher.py` switches the standard `*_controller`s back on, which PlayMotion needs. If those controllers are stopped when the robot boots, the start/stop is what turns them on.

The script covers both. It loads `telepresence_motions.yaml` directly with `rosparam load`. It also runs the start/stop step automatically, but only when `arm_controller` or `torso_controller` is not running. The first hardware session will show which cause applies. If it is always the first, step 4 never triggers.

Upstream also has `tiago_real.launch motion:=extend`, where `arm_motion.py` swaps controllers around the motion. It was not used here: `arm_motion.py` and `tp_controller_switcher.py` start at the same time and race to switch the same controllers. An explicit sequence is easier to reason about on a real arm.

## 3. ReadMe `[VERIFY]` items the code answers

| ReadMe item | What the repo shows |
|---|---|
| §7.8: does the ROS–TCP endpoint need its own terminal? | No. `tiago_real.launch` includes `ros_tcp_endpoint/endpoint.launch` with `tcp_ip`/`tcp_port` (default port 10000). Unity's `Assets/Resources/ROSConnectionPrefab.prefab` connects to `10.205.3.26:10000` with *Connect on start*. |
| §3: `tracking/*.py` committed? | Yes. They are now `ros_ws/src/puppet_bringup/scripts/`, with topics and offsets as ROS params (same defaults). |
| §3: `natnet_ros_cpp` present? | Yes. Identical to the pinned upstream commit `abdde99` (minus logo images). `optitrack_ros_communication` is identical to the pinned commit `ebe3999`. |
| §10: main scene | `unity/PUPPET_Unity` builds `Assets/MAIN PUPPET SCENE.unity`. `PUPPET TRAINING.unity` is listed (disabled) in build settings, but the scene file is not committed, only its folder. |
| §8.2: object topic name | Unknown until the next session. The topic is now a setting (`PUCK_TOPIC`). If it is not published, `./puppet check` lists the `/natnet_ros/*/pose` topics that are. |
| UDP relay nodes | `optitrack_nodes.launch` starts 10 UDP relay nodes sending to `10.205.3.4` by default. No Unity script uses UDP sockets. They are kept on (`MOCAP_UDP_CLIENT=true`) to match the operator's command. Turn them off once nothing else at `10.205.3.4` needs them. |

## 4. Fixed in this branch

1. **`dependencies/tiago_public_ws.rosinstall` could not be imported.** It mixed the rosinstall list form with vcstool's `.repos` keys. `vcs` reported `does not provide the necessary information: 'local-name'` and `wstool` reported `Unknown key ROS-TCP-Endpoint`. It is now standard rosinstall: 53 entries, same URLs and pinned commits. Both tools parse it.
2. **Python ROS nodes were not executable in git** (mode 100644). Packages without `catkin_install_python`, for example `optitrack_ros_communication`'s `generate_udp_nodes.py`, cannot be launched from a fresh devel-space build. All node scripts are now 100755.
3. **`tp_controller_switcher.py` called `rospy.logerror`**, which does not exist. It should be `rospy.logerr`. A failed controller switch would raise `AttributeError` instead of logging. This fix only reaches the robot after a `pal_deploy` of `tiago_telepresence_controllers`.
4. **`.gitignore` excluded `*.png`, `*.jpg`, `*.jpeg`, `*.tga`, `*.exr`, `*.psd`**, while `.gitattributes` sends the same types to Git LFS. As a result, 294 `.png.meta`, 116 `.jpg.meta` and 61 `.exr.meta` files are committed with no texture next to them. The ignore rules are removed and the file is de-duplicated (it had three copies of the ROS block). **The textures still have to be committed from the MSI working copy.**
5. Committed `.DS_Store` files are removed.
6. `scripts/setup_workspace.sh` rebuilds `~/tiago_public_ws` from the pinned sources. It installs the NatNet SDK, runs `rosdep`, links `puppet_bringup` into the workspace and runs `catkin build`.
7. `validation/requirements.txt` lists the pip packages the validation scripts import. They are unpinned; run `pip freeze` on archimedes to pin them.

## 5. Recommended next, not done here

In rough order of value:

1. **Commit the Unity textures** from the MSI copy (LFS). Without them, a clone opens with missing materials.
2. **Remove the second Unity copy and the build binaries.** `unity/Assets`, `unity/ProjectSettings` and the rest are an older project (build scene `vrstuff.unity`). Next to them sit a Linux player build: `vrstuff2.x86_64`, `vrstuff2_Data/` (82 MB) and `UnityPlayer.so` (31 MB). The current project is `unity/PUPPET_Unity`. Builds belong in GitHub Releases. That cuts most of the 719 MB checkout. Demo content (TextMesh Pro examples, the `com.tnd.markers` Sponza demo) can go too.
3. **Fix LFS patterns for upper-case extensions.** `Sponza_Modular.FBX` was committed as a raw blob because `*.fbx` does not match `.FBX` on case-sensitive Linux (clone warning: *"Encountered 1 file that should have been a pointer"*). Use `*.[fF][bB][xX]`, or `git lfs track` both spellings.
4. **Move session calibration out of the APK.** The ROS IP (`ROSConnectionPrefab`) and the yaw offset (`TiagoMocapFollower.sceneYawOffset`, about −5 to −6) are Inspector values. Changing them means rebuilding and redeploying to the Quest. Reading them at start from ROS params (e.g. `/puppet/yaw_offset_deg`, set from `config/puppet.env`) would make calibration part of `./puppet up`.
5. **Deploy a single TIAGo-side launch** (PlayMotion + telepresence) with `pal_deploy`, once the sequence in §1 is confirmed on hardware. The script would then need one SSH window instead of two.
6. **Docker image for the mini PC** (`ros:noetic` + pinned workspace + NatNet SDK). Any Linux machine could then be an "archimedes" in one command. The container needs `--network host`.
7. **Recording.** Add a `./puppet record <participant> <trial>` that starts `rosbag record` with the topic list the validation pipeline expects. That way the data side is as repeatable as the startup.
8. Small things: `validation/rebuild_analysis_bundle.py` hard-codes `/home/mahika/...`. `tiago_telepresence_controllers/cmake/` contains generated catkin files. Its scripts use `#!/usr/bin/env python`, which is fine once installed on the robot but not on a plain Noetic devel space.

## What was tested

In a `ros:noetic-ros-base` Docker container (arm64):

- `puppet_bringup` and `optitrack_ros_communication` build with `catkin_make`. `roslaunch --nodes puppet_bringup mocap.launch` resolves, including the NatNet and UDP includes.
- Fake OptiTrack poses produce the expected `/odom_mocap` and `/puck_mocap` values. Topic parameters and `offset_z` work.
- `./puppet doctor` and `./puppet check` against a robot-less master print the expected ok/warn/FAIL lines. The puck check lists the real candidate topic.
- tmux window start, Ctrl+C stop and dead-pane detection work for the `mocap` process.
- `shellcheck` is clean, apart from intentional remote-expansion warnings.
- The old `.rosinstall` fails in `vcs` and `wstool`. The new one parses in both.

**Not tested:** anything that touches TIAGo (SSH, PlayMotion, telepresence, controller switching, `extend`), real NatNet/Motive, the full `setup_workspace.sh` build, or Unity.

## First hardware session (2026-10-26)

`./puppet up` ran end to end: OptiTrack bridge, `extend`, telepresence, Quest 2 connected, `./puppet check` all green, `./puppet down` back to standard controllers.

**Confirmed**
- §2 was right: loading `telepresence_motions.yaml` was enough. `extend` succeeded on the first try, and the start/stop workaround (step 4) never triggered.
- PAL starts `/play_motion` at boot, so the script reuses it and does not stop it. Unity's B button keeps working.

**Found and fixed in this branch**
1. **The Quest B button did nothing.** `arm_motion.py` read the list of `*_tp_controller`s once at startup. It starts in the same launch file as the spawner, so the list was empty. Every switch was then a no-op, and PlayMotion failed with `No controller was found for joint 'torso_lift_joint'`. It now reads the list on every switch.
   - Until that file is redeployed on TIAGo, `./puppet up` restarts the node after telepresence is up (`RESTART_ARM_MOTION=true`, window `arm_motion`).
2. **E-stop.** TIAGo had booted with the e-stop pressed: `/joint_states` was silent and several startup jobs had timed out. `doctor` now reads `/power_status/is_emergency` on TIAGo and gives the exact recovery steps. After releasing the e-stop, the **blinking green button** must be pressed to power the motors again.
3. **Accounts without sudo or a home directory.** archimedes LDAP users (e.g. `rsagastegui`) get no `/home` (autofs) and no sudo, and cannot read `/home/mahika`. `scripts/setup_workspace.sh --mocap-only` needs none of that.
   - It builds only the three packages archimedes runs, from this repo, in a few seconds, and gets tmux from micromamba.
   - Without a home, use `export HOME=/var/tmp/$USER` first, since `/var/tmp` survives reboots.
4. **Noisy endpoint log.** `check` used to connect to port 10000, and every probe logged `Connection from … / No more data` in the telepresence window. It now asks TIAGo whether the port is listening (`ss`).

**Open: arm mapping depends on the start pose.** `arm_tp_controller` applies the Quest command in the gripper frame, frozen when the controller starts (`H_0_N = H_0_N_initial * H_N`). `ArmCommander.cs` sends hand deltas in a base-like frame:
- position as `(z, -x, y)`;
- orientation as `(z, x, y, w)`, which does not match the position's handedness.

So the mapping changes with the pose the arm is in when B finishes:
- after `extend`, up↔down and left↔right are swapped;
- after `offer`, up/down comes out sideways.

Redefining `offer` as a base-aligned pose was tried and made the motion worse, so it was reverted. Fix this in simulation (Gazebo TIAGo with the telepresence controllers) before the next hardware attempt: express the command in `start_link` in the controller, and fix the quaternion conversion in Unity.

**Controls (from the scene wiring):**
- Right A turns head and arm following on and off together. The background goes black while it is on.
- Right B toggles `offer` ↔ `home`, and works only while following is on.
- Triggers and grips drive the gripper.
- Left X and Y control speaker and microphone.
