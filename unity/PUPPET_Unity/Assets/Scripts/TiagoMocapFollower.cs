using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Nav;

public class TiagoMocapFollower : MonoBehaviour
{
    [Header("ROS")]
    public string topicName = "/odom_mocap";

    [Header("Smoothing")]
    public float smoothing = 10f;

    [Header("Position Settings")]
    public float positionThreshold = 0.002f;
    public bool lockHeight = true;
    public float fixedHeight = 0f;

    [Header("Scene Alignment")]
    public float sceneYawOffset = 0f;

    [Header("Debug")]
    public bool debugLogs = true;
    public bool drawDebugRays = true;

    private ROSConnection ros;

    private Vector3 targetPosition;
    private Quaternion targetRotation;

    private Vector3 smoothPosition;
    private Quaternion smoothRotation;

    private bool initialized = false;
    private Vector3 positionOffset;

    private Vector3 lastMappedPos;
    private bool hasLastMappedPos = false;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();

        ros.Subscribe<OdometryMsg>(
            topicName,
            OdomCallback
        );
    }

    void OdomCallback(OdometryMsg msg)
    {
        // ---------------- POSITION ----------------

        float rosX =
            (float)msg.pose.pose.position.x;

        float rosY =
            (float)msg.pose.pose.position.y;

        float rosZ =
            (float)msg.pose.pose.position.z;

        /*
         * Explicit mapping instead of swap/invert toggles.
         *
         * Try this as the primary mapping:
         * Unity X = rosX
         * Unity Y = rosZ
         * Unity Z = rosY
         */
        Vector3 mappedPos = new Vector3(
            rosX,
            rosZ,
            rosY
        );

        if (lockHeight)
            mappedPos.y = fixedHeight;

        if (debugLogs)
        {
            if (hasLastMappedPos)
            {
                Vector3 delta =
                    mappedPos -
                    lastMappedPos;

                Debug.Log(
                    $"DELTA → " +
                    $"X:{delta.x:F3}  " +
                    $"Y:{delta.y:F3}  " +
                    $"Z:{delta.z:F3}"
                );
            }

            Debug.Log(
                $"ROS Pos → " +
                $"X:{rosX:F3} " +
                $"Y:{rosY:F3} " +
                $"Z:{rosZ:F3}"
            );

            Debug.Log(
                $"Mapped Pos → " +
                $"X:{mappedPos.x:F3} " +
                $"Y:{mappedPos.y:F3} " +
                $"Z:{mappedPos.z:F3}"
            );
        }

        lastMappedPos = mappedPos;
        hasLastMappedPos = true;

        // ---------------- ROTATION ----------------

        var q =
            msg.pose.pose.orientation;

        Quaternion rosQuat =
            new Quaternion(
                (float)q.x,
                (float)q.y,
                (float)q.z,
                (float)q.w
            );

        // ROS → Unity quaternion mapping
        Quaternion mappedRotation =
            new Quaternion(
                -rosQuat.y,
                 rosQuat.z,
                 rosQuat.x,
                 rosQuat.w
            );

        // Fix: invert yaw sign so real-world right/left match Unity
        Vector3 mappedEuler =
            mappedRotation.eulerAngles;

        mappedRotation =
            Quaternion.Euler(
                mappedEuler.x,
                -mappedEuler.y,
                mappedEuler.z
            );

        // Optional scene alignment so "forward" points toward the table
        targetRotation =
            Quaternion.Euler(
                0f,
                sceneYawOffset,
                0f
            )
            *
            mappedRotation;

        // ---------------- INITIAL POSITION ALIGNMENT ----------------

        if (!initialized)
        {
            positionOffset =
                transform.position -
                mappedPos;

            smoothPosition =
                transform.position;

            smoothRotation =
                transform.rotation;

            initialized = true;
        }

        Vector3 correctedPos =
            positionOffset +
            mappedPos;

        if (
            Vector3.Distance(
                targetPosition,
                correctedPos
            )
            >
            positionThreshold
        )
        {
            targetPosition =
                correctedPos;
        }
    }

    void Update()
    {
        if (!initialized)
            return;

        smoothPosition =
            Vector3.Lerp(
                smoothPosition,
                targetPosition,
                Time.deltaTime *
                smoothing
            );

        smoothRotation =
            Quaternion.Slerp(
                smoothRotation,
                targetRotation,
                Time.deltaTime *
                smoothing
            );

        transform.position =
            smoothPosition;

        transform.rotation =
            smoothRotation;
    }

    void OnDrawGizmos()
    {
        if (!drawDebugRays)
            return;

        Gizmos.color =
            Color.blue;

        Gizmos.DrawRay(
            transform.position,
            transform.forward *
            0.5f
        );

        Gizmos.color =
            Color.red;

        Gizmos.DrawRay(
            transform.position,
            transform.right *
            0.5f
        );
    }
}