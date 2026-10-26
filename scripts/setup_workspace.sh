#!/usr/bin/env bash
# Fresh mini-PC setup (Ubuntu 20.04 with ROS Noetic already installed).
#
# Rebuilds ~/tiago_public_ws from the pinned sources in dependencies/tiago_public_ws.rosinstall,
# links puppet_bringup into it, and builds everything with catkin build (catkin_make broke some
# PAL packages during development). Safe to re-run: existing checkouts are left as they are.
#
#   scripts/setup_workspace.sh            # workspace in ~/tiago_public_ws
#   TIAGO_WS=/path/to/ws scripts/setup_workspace.sh
#   scripts/setup_workspace.sh --mocap-only
#
# --mocap-only needs no sudo and builds only what archimedes runs (natnet_ros_cpp,
# optitrack_ros_communication, puppet_bringup, all from this repo) into ~/puppet_ws in seconds.
# The PAL packages are not needed on archimedes: telepresence and PlayMotion run on TIAGo.
# This is the route for lab accounts without sudo (tmux then comes from micromamba).
#
# This only sets up the mini PC. TIAGo keeps its own deployed workspace (~/deployed_ws_tele),
# which is updated with pal_deploy (see ros_ws/src/tiago_telepresence_controllers/README.md).

set -euo pipefail

PUPPET_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIAGO_WS="${TIAGO_WS:-$HOME/tiago_public_ws}"

if [[ "${1:-}" == --mocap-only ]]; then
  PUPPET_WS="${PUPPET_WS:-$HOME/puppet_ws}"
  set +u; source /opt/ros/noetic/setup.bash; set -u

  if ! command -v tmux >/dev/null; then
    echo "==> tmux (user space, via micromamba)"
    mkdir -p "$HOME/.local/bin"
    [[ -x "$HOME/.local/bin/micromamba" ]] || \
      curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C "$HOME/.local" bin/micromamba
    "$HOME/.local/bin/micromamba" create -y -q -r "$HOME/mamba" -n tools -c conda-forge tmux >/dev/null
    ln -sf "$HOME/mamba/envs/tools/bin/tmux" "$HOME/.local/bin/tmux"
    echo "add to PATH: export PATH=\$HOME/.local/bin:\$PATH"
  fi

  echo "==> NatNet SDK for natnet_ros_cpp"
  sdk="$PUPPET_ROOT/ros_ws/src/natnet_ros_cpp"
  [[ -d "$sdk/deps/NatNetSDK/lib" ]] || (cd "$sdk" && bash install_sdk.sh)

  echo "==> $PUPPET_WS (mocap packages only)"
  mkdir -p "$PUPPET_WS/src"
  for p in natnet_ros_cpp optitrack_ros_communication puppet_bringup; do
    ln -sfn "$PUPPET_ROOT/ros_ws/src/$p" "$PUPPET_WS/src/$p"
  done
  cd "$PUPPET_WS"
  catkin config --extend /opt/ros/noetic >/dev/null
  catkin build --no-status

  local_env="$PUPPET_ROOT/config/puppet.local.env"
  if ! grep -qs '^TIAGO_WS_SETUP=' "$local_env"; then
    echo "TIAGO_WS_SETUP=$PUPPET_WS/devel/setup.bash" >> "$local_env"
    echo "wrote TIAGO_WS_SETUP to $local_env"
  fi
  echo
  echo "Done. Next: ./puppet doctor"
  exit 0
fi

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
