#!/usr/bin/env bash
# Fresh mini-PC setup (Ubuntu 20.04 with ROS Noetic already installed).
#
# Rebuilds ~/tiago_public_ws from the pinned sources in dependencies/tiago_public_ws.rosinstall,
# links puppet_bringup into it, and builds everything with catkin build (catkin_make broke some
# PAL packages during development). Safe to re-run: existing checkouts are left as they are.
#
#   scripts/setup_workspace.sh            # workspace in ~/tiago_public_ws
#   TIAGO_WS=/path/to/ws scripts/setup_workspace.sh
#
# This only sets up the mini PC. TIAGo keeps its own deployed workspace (~/deployed_ws_tele),
# which is updated with pal_deploy (see ros_ws/src/tiago_telepresence_controllers/README.md).

set -euo pipefail

PUPPET_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIAGO_WS="${TIAGO_WS:-$HOME/tiago_public_ws}"

echo "==> System packages"
sudo apt-get update
sudo apt-get install -y python3-vcstool python3-catkin-tools python3-rosdep tmux wget

set +u; source /opt/ros/noetic/setup.bash; set -u

echo "==> Sources into $TIAGO_WS/src (pinned commits, existing checkouts skipped)"
mkdir -p "$TIAGO_WS/src"
vcs import --skip-existing --input "$PUPPET_ROOT/dependencies/tiago_public_ws.rosinstall" "$TIAGO_WS/src"

# puppet_bringup is built inside the same workspace, so there is a single setup.bash to source.
ln -sfn "$PUPPET_ROOT/ros_ws/src/puppet_bringup" "$TIAGO_WS/src/puppet_bringup"

echo "==> NatNet SDK for natnet_ros_cpp"
if [[ -d "$TIAGO_WS/src/natnet_ros_cpp/deps/NatNetSDK/lib" ]]; then
  echo "already installed"
else
  (cd "$TIAGO_WS/src/natnet_ros_cpp" && bash install_sdk.sh)
fi

echo "==> rosdep"
[[ -f /etc/ros/rosdep/sources.list.d/20-default.list ]] || sudo rosdep init
rosdep update
rosdep install --from-paths "$TIAGO_WS/src" --ignore-src --rosdistro noetic -r -y

echo "==> catkin build"
cd "$TIAGO_WS"
catkin config --extend /opt/ros/noetic >/dev/null
catkin build

echo
echo "Done. Next:"
echo "  1. Check config/puppet.env (IPs, TIAGo host, rigid-body topics)."
echo "  2. ssh-copy-id pal@tiago-38c   (optional, avoids password prompts)"
echo "  3. ./puppet doctor"
