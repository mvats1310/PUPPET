using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using RosMessageTypes.Nav;

public class FollowOptiTrackBase : MonoBehaviour
{
    [Header("OptiTrack")]
    public string optiTrackTopic = "/natnet_ros/umh_4/pose";

    [Header("Base Rotation (ROS)")]
    public string baseRotationTopic = "/mobile_base_controller/odom";

    [Header("Position")]
    public Vector3 positionOffset = Vector3.zero;
    public Vector3 headToBaseOffset = new Vector3(0.22f, 0f, 0f);

    [Header("Height Lock")]
    public bool lockHeight = true;
    public float fixedHeight = -0.3f;

    [Header("Rotation")]
    public float yawOffsetDegrees = -150f;

    [Header("Smoothing")]
    public float smoothing = 10f;
    public float positionDeadZone = 0.005f;

    [Header("Axis Mapping")]
    public bool swapXZ = true;
    public bool invertX = false;
    public bool invertZ = true;

    [Header("Debug")]
    public bool debugMode = false;

    private ROSConnection ros;

    // Written by callbacks, read by Update — all on known threads
    private Vector3 latestHeadPos;
    private bool haveHeadPos = false;

    private float latestRosYaw = 0f;
    private bool haveOdom = false;

    // Computed and applied on main thread only
    private Vector3 targetPos;
    private Quaternion targetRot = Quaternion.identity;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<PoseStampedMsg>(optiTrackTopic, OptiCallback);
        ros.Subscribe<OdometryMsg>(baseRotationTopic, OdomCallback);
        if (debugMode) Debug.Log("[FollowOptiTrackBase] Started");
    }

    void OptiCallback(PoseStampedMsg msg)
    {
        float rosX = (float)msg.pose.position.x;
        float rosY = (float)msg.pose.position.y;
        float rosZ = (float)msg.pose.position.z;

        Vector3 mapped = new Vector3(-rosY, rosZ, rosX);
        if (swapXZ) { float tmp = mapped.x; mapped.x = mapped.z; mapped.z = tmp; }
        if (invertX) mapped.x = -mapped.x;
        if (invertZ) mapped.z = -mapped.z;

        latestHeadPos = mapped + positionOffset;
        haveHeadPos = true;
    }

    void OdomCallback(OdometryMsg msg)
    {
        Quaternion q = new Quaternion(
            (float)msg.pose.pose.orientation.x,
            (float)msg.pose.pose.orientation.y,
            (float)msg.pose.pose.orientation.z,
            (float)msg.pose.pose.orientation.w
        );

        // Direct yaw extraction from pure Z-rotation quaternion
        latestRosYaw = 2f * Mathf.Atan2(q.z, q.w) * Mathf.Rad2Deg;
        haveOdom = true;
    }

    void Update()
    {
        if (!haveHeadPos || !haveOdom) return;

        // Compute rotation on main thread
        float unityYaw = -latestRosYaw + yawOffsetDegrees;
        Quaternion baseRotation = Quaternion.Euler(0f, unityYaw, 0f);

        // Compute base position using freshly computed rotation
        Vector3 headPos = latestHeadPos;
        if (lockHeight) headPos.y = fixedHeight;

        Vector3 localOffset = new Vector3(headToBaseOffset.x, 0f, headToBaseOffset.z);
        Vector3 rotatedOffset = baseRotation * localOffset;
        Vector3 basePos = headPos - rotatedOffset;
        if (lockHeight) basePos.y = fixedHeight;

        if (!haveHeadPos || Vector3.Distance(basePos, targetPos) > positionDeadZone)
            targetPos = basePos;

        targetRot = baseRotation;

        if (debugMode)
            Debug.Log($"[Update] rosYaw={latestRosYaw:F1}° unityYaw={unityYaw:F1}° rotatedOffset={rotatedOffset:F3} base={basePos:F3}");

        // Apply
        if (smoothing <= 0f)
        {
            transform.position = targetPos;
            transform.rotation = targetRot;
        }
        else
        {
            float t = Mathf.Clamp01(Time.deltaTime * smoothing);
            transform.position = Vector3.Lerp(transform.position, targetPos, t);
            transform.rotation = Quaternion.Slerp(transform.rotation, targetRot, t);
        }
    }

    void OnDestroy()
    {
        if (ros != null)
        {
            ros.Unsubscribe(optiTrackTopic);
            ros.Unsubscribe(baseRotationTopic);
        }
    }
}