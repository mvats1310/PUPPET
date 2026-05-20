using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;

public class ObjectOptiTrack : MonoBehaviour
{
    [Header("OptiTrack")]
    public string topicName = "/natnet_ros/umh_3/pose";

    [Header("Position")]
    public Vector3 positionOffset = Vector3.zero;

    [Header("Rotation")]
    public Vector3 rotationOffsetEuler = Vector3.zero;

    [Header("Smoothing")]
    public float smoothing = 0f;

    [Header("Axis Mapping")]
    public bool swapXZ = true;
    public bool invertX = false;
    public bool invertZ = true;

    [Header("Debug")]
    public bool debugMode = false;

    private ROSConnection ros;

    private Vector3 targetPos;
    private Quaternion targetRot;
    private bool havePose = false;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<PoseStampedMsg>(topicName, PoseCallback);

        if (debugMode)
            Debug.Log($"[ObjectOptiTrack] Subscribed to {topicName}");
    }

    void PoseCallback(PoseStampedMsg msg)
    {
        // -------------------------
        // POSITION
        // -------------------------
        float rosX = (float)msg.pose.position.x;
        float rosY = (float)msg.pose.position.y;
        float rosZ = (float)msg.pose.position.z;

        Vector3 mapped = new Vector3(-rosY, rosZ, rosX);

        if (swapXZ)
        {
            float tmp = mapped.x;
            mapped.x = mapped.z;
            mapped.z = tmp;
        }
        if (invertX) mapped.x = -mapped.x;
        if (invertZ) mapped.z = -mapped.z;

        targetPos = mapped + positionOffset;

        // -------------------------
        // ROTATION
        // -------------------------
        Quaternion q_ros = new Quaternion(
            (float)msg.pose.orientation.x,
            (float)msg.pose.orientation.y,
            (float)msg.pose.orientation.z,
            (float)msg.pose.orientation.w
        );

        Vector3 forwardRos = q_ros * Vector3.right;
        Vector3 upRos      = q_ros * Vector3.forward;

        Vector3 forwardUnity = new Vector3(-forwardRos.y, forwardRos.z, forwardRos.x);
        Vector3 upUnity      = new Vector3(-upRos.y, upRos.z, upRos.x);

        if (swapXZ)
        {
            float tmp = forwardUnity.x;
            forwardUnity.x = forwardUnity.z;
            forwardUnity.z = tmp;

            tmp = upUnity.x;
            upUnity.x = upUnity.z;
            upUnity.z = tmp;
        }
        if (invertX)
        {
            forwardUnity.x = -forwardUnity.x;
            upUnity.x = -upUnity.x;
        }
        if (invertZ)
        {
            forwardUnity.z = -forwardUnity.z;
            upUnity.z = -upUnity.z;
        }

        if (forwardUnity.sqrMagnitude < 1e-6f)
            forwardUnity = Vector3.forward;

        targetRot = Quaternion.LookRotation(forwardUnity, upUnity);

        // Optional correction
        targetRot = targetRot * Quaternion.Euler(rotationOffsetEuler);

        havePose = true;

        if (debugMode)
            Debug.Log($"[ObjectOptiTrack] pos={targetPos}");
    }

    void Update()
    {
        if (!havePose) return;

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
            ros.Unsubscribe(topicName);
    }
}
