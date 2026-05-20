using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Nav;

public class TiagoBaseOdomSubscriber : MonoBehaviour
{
    [Header("ROS")]
    public string topicName = "/mobile_base_controller/odom";
    private ROSConnection ros;

    [Header("Target")]
    public string targetLinkName = "base_link";
    private Transform baseLinkTransform;

    [Header("Smoothing")]
    public float positionSmoothing = 10f;
    public float rotationSmoothing = 10f;
    public float positionThreshold = 0.002f;

    [Header("Diagnostics")]
    public bool debugLogs = false;
    public bool invertYaw = false;
    public bool flipHandedness = false;

    private Vector3 targetPos;
    private Quaternion targetRot;
    private Vector3 smoothPos;
    private Quaternion smoothRot;

    private bool firstOdom = false;
    private Vector3 worldOffset;
    private Quaternion rotOffset;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<OdometryMsg>(topicName, OnOdom);

        foreach (var t in GetComponentsInChildren<Transform>(true))
        {
            if (t.name == targetLinkName)
            {
                baseLinkTransform = t;
                break;
            }
        }

        if (TryGetComponent<Rigidbody>(out var rb))
        {
            rb.isKinematic = true;
            rb.useGravity = false;
        }
    }

    void OnOdom(OdometryMsg msg)
    {
        float rx = (float)msg.pose.pose.position.x;
        float ry = (float)msg.pose.pose.position.y;
        float rz = (float)msg.pose.pose.position.z;

        // ✅ Fixed mapping: ROS forward(X) → Unity Z, ROS left(Y) → Unity X
        Vector3 rosPosWorld = new Vector3(ry, rz, rx);

        Quaternion q_ros = new Quaternion(
            (float)msg.pose.pose.orientation.x,
            (float)msg.pose.pose.orientation.y,
            (float)msg.pose.pose.orientation.z,
            (float)msg.pose.pose.orientation.w
        );

        // Correct ROS basis vectors
        Vector3 forwardRos = q_ros * new Vector3(1, 0, 0); // ROS +X = forward
        Vector3 upRos      = q_ros * new Vector3(0, 0, 1); // ROS +Z = up

        // ROS → Unity axis mapping
        Vector3 forwardUnity = new Vector3(forwardRos.y, forwardRos.z, forwardRos.x);
        Vector3 upUnity      = new Vector3(upRos.y,      upRos.z,      upRos.x);

        if (flipHandedness)
        {
            forwardUnity.z = -forwardUnity.z;
            upUnity.z = -upUnity.z;
        }

        if (forwardUnity.sqrMagnitude < 1e-6f) forwardUnity = Vector3.forward;
        if (upUnity.sqrMagnitude < 1e-6f)      upUnity = Vector3.up;
        forwardUnity.Normalize();
        upUnity.Normalize();

        if (invertYaw)
            forwardUnity.x = -forwardUnity.x;

        Quaternion unityRot = Quaternion.LookRotation(forwardUnity, upUnity);

        var applyTo = baseLinkTransform != null ? baseLinkTransform : transform;

        if (!firstOdom)
        {
            worldOffset = applyTo.position - rosPosWorld;
            rotOffset = applyTo.rotation * Quaternion.Inverse(unityRot);
            smoothPos = applyTo.position;
            smoothRot = applyTo.rotation;
            firstOdom = true;

            if (debugLogs)
                Debug.Log($"[Odom] Initialized at pos={rosPosWorld} yaw={unityRot.eulerAngles.y:F1}");
        }

        Vector3 newPos = worldOffset + rosPosWorld;

        if (Vector3.Distance(targetPos, newPos) > positionThreshold)
            targetPos = newPos;

        targetRot = rotOffset * unityRot;
    }

    void Update()
    {
        if (!firstOdom) return;

        var applyTo = baseLinkTransform != null ? baseLinkTransform : transform;

        smoothPos = Vector3.Lerp(smoothPos, targetPos, Time.deltaTime * positionSmoothing);
        smoothRot = Quaternion.Slerp(smoothRot, targetRot, Time.deltaTime * rotationSmoothing);

        applyTo.position = smoothPos;
        applyTo.rotation = smoothRot;

        if (debugLogs)
            Debug.Log($"[Odom] Pos={smoothPos:F2} Yaw={smoothRot.eulerAngles.y:F1}°");
    }
}