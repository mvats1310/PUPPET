using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Nav;

public class PuckMocapFollower : MonoBehaviour
{
    [Header("ROS")]
    [SerializeField]
    private string topicName = "/puck_mocap";

    [Header("Gripper")]
    [Tooltip("Transform at the CENTER between TIAGo's gripper fingers.")]
    [SerializeField]
    private Transform gripperHoldPoint;

    [Header("Tracking")]
    [SerializeField]
    private bool followPosition = true;

    [SerializeField]
    private bool followRotation = true;

    [Header("Smoothing")]
    [SerializeField]
    private float positionSmoothSpeed = 10f;

    [SerializeField]
    private float rotationSmoothSpeed = 10f;

    [Header("Mocap adjustment")]
    [Tooltip("Offset from UMH rigid-body origin to the actual center of the object.")]
    [SerializeField]
    private Vector3 positionOffset = Vector3.zero;

    [SerializeField]
    private Vector3 rotationOffset = Vector3.zero;


    private ROSConnection ros;

    private Vector3 targetPosition;
    private Quaternion targetRotation;

    private Vector3 latestRosPosition;
    private Quaternion latestRosRotation;

    // Reference used to map ROS movement into Unity
    private Vector3 referenceRosPosition;
    private Quaternion referenceRosRotation;

    private Vector3 referenceUnityPosition;
    private Quaternion referenceUnityRotation;

    private bool initialized = false;
    private bool hasTargetPose = false;

    // TRUE while TIAGo is holding the object
    private bool isHeld = false;


    private void Start()
    {
        targetPosition = transform.position;
        targetRotation = transform.rotation;

        ros = ROSConnection.GetOrCreateInstance();

        ros.Subscribe<OdometryMsg>(
            topicName,
            ReceivePuckPose
        );

        Debug.Log("Puck subscribed to: " + topicName);
    }


    private void Update()
    {
        /*
         * ----------------------------------------------------
         * OBJECT CURRENTLY HELD
         * ----------------------------------------------------
         *
         * Do NOT use OptiTrack while gripping.
         *
         * The virtual cube follows the virtual gripper exactly.
         */
        if (isHeld)
        {
            if (gripperHoldPoint != null)
            {
                transform.position = gripperHoldPoint.position;

                // Optional:
                // Uncomment if you want the object orientation
                // locked to the gripper as well.
                //
                // transform.rotation = gripperHoldPoint.rotation;
            }

            return;
        }


        /*
         * ----------------------------------------------------
         * OBJECT FREE
         * ----------------------------------------------------
         *
         * Follow OptiTrack normally.
         */
        if (!hasTargetPose)
            return;


        float positionLerpFactor =
            1f - Mathf.Exp(
                -positionSmoothSpeed * Time.deltaTime
            );

        float rotationLerpFactor =
            1f - Mathf.Exp(
                -rotationSmoothSpeed * Time.deltaTime
            );


        if (followPosition)
        {
            transform.position = Vector3.Lerp(
                transform.position,
                targetPosition,
                positionLerpFactor
            );
        }


        if (followRotation)
        {
            transform.rotation = Quaternion.Slerp(
                transform.rotation,
                targetRotation,
                rotationLerpFactor
            );
        }
    }


    private void ReceivePuckPose(OdometryMsg msg)
    {
        /*
         * ROS -> Unity coordinate conversion
         */
        Vector3 mappedPosition = new Vector3(
            (float)msg.pose.pose.position.x,
            (float)msg.pose.pose.position.z,
            (float)msg.pose.pose.position.y
        );


        Quaternion mappedRotation = new Quaternion(
            (float)-msg.pose.pose.orientation.y,
            (float)msg.pose.pose.orientation.z,
            (float)msg.pose.pose.orientation.x,
            (float)msg.pose.pose.orientation.w
        );

        mappedRotation =
            Quaternion.Normalize(mappedRotation);


        latestRosPosition = mappedPosition;
        latestRosRotation = mappedRotation;


        /*
         * First mocap measurement establishes the reference.
         */
        if (!initialized)
        {
            ReanchorMocap();

            initialized = true;
            hasTargetPose = true;

            Debug.Log(
                "Puck mocap reference initialized."
            );

            return;
        }


        /*
         * If the cube is in the gripper, keep receiving
         * mocap data but DO NOT use it to move the cube.
         */
        if (isHeld)
            return;


        Quaternion relativeRotation =
            mappedRotation *
            Quaternion.Inverse(referenceRosRotation);


        /*
         * Translation of the UMH since our reference point.
         */
        Vector3 relativePosition =
            mappedPosition -
            referenceRosPosition;


        /*
         * Offset compensation.
         *
         * Important because the UMH is not mounted exactly
         * at the object's center.
         */
        Vector3 initialOffset =
            referenceRosRotation *
            positionOffset;

        Vector3 currentOffset =
            mappedRotation *
            positionOffset;

        Vector3 offsetChange =
            currentOffset -
            initialOffset;


        targetPosition =
            referenceUnityPosition +
            relativePosition +
            offsetChange;


        targetRotation =
            relativeRotation *
            referenceUnityRotation *
            Quaternion.Euler(rotationOffset);


        hasTargetPose = true;
    }


    /*
     * ========================================================
     * CALL THIS WHEN THE GRIPPER CLOSES ON THE PUCK
     * ========================================================
     */
    public void GrabObject()
    {
        if (isHeld)
            return;

        isHeld = true;

        Debug.Log("PUCK GRABBED - following gripper");
    }


    /*
     * ========================================================
     * CALL THIS WHEN THE GRIPPER OPENS
     * ========================================================
     */
    public void ReleaseObject()
    {
        if (!isHeld)
            return;


        /*
         * Cube is already sitting at the gripperHoldPoint
         * because Update() has been moving it there.
         *
         * Therefore THIS exact pose becomes the released pose.
         */
        isHeld = false;


        /*
         * Critical:
         *
         * Re-anchor mocap HERE.
         *
         * Without this, mocap would immediately try to pull
         * the cube back toward its old coordinate mapping,
         * causing the sideways snap you are currently seeing.
         */
        ReanchorMocap();


        targetPosition = transform.position;
        targetRotation = transform.rotation;


        Debug.Log(
            "PUCK RELEASED - mocap re-anchored at release position"
        );
    }


    /*
     * Create a new relationship between the current physical
     * OptiTrack pose and the current Unity pose.
     */
    private void ReanchorMocap()
    {
        referenceRosPosition =
            latestRosPosition;

        referenceRosRotation =
            latestRosRotation;

        referenceUnityPosition =
            transform.position;

        referenceUnityRotation =
            transform.rotation;
    }


    private void OnDestroy()
    {
        if (ros != null)
        {
            ros.Unsubscribe(topicName);
        }
    }
}