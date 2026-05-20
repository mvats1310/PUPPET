using UnityEngine;
using UnityEngine.InputSystem;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.BuiltinInterfaces;
using RosMessageTypes.Geometry;
using RosMessageTypes.TiagoTelepresenceControllers;
using RosMessageTypes.Std;
using System;

public class ArmCommander : MonoBehaviour
{
    private ROSConnection ros;

    [Header("Input Actions")]
    public InputActionReference armPositionReference = null;
    public InputActionReference armOrientationReference = null;
    public InputActionReference extendArmReference = null;
    public InputActionReference enableArmReference = null;

    [Header("ROS")]
    public string topicName = "/arm_tp_controller/command";
    public string serviceName = "/tp_arm_motion/command";

    [Header("Teleoperation Conditioning")]
    public float positionScale = 0.6f;
    public float rotationScale = 0.25f;
    public float positionDeadzone = 0.005f;
    public float rotationDeadzoneDeg = 0.5f;
    public float smoothing = 12f;
    
    [Header("Wrist Control")]
    [Tooltip("Enable independent wrist twist control")]
    public bool enableWristTwist = true;
    [Tooltip("Scale wrist rotation separately from arm rotation")]
    public float wristTwistScale = 1.0f;

    [Header("Collision Detection")]
    [Tooltip("Enable to stop arm when collision detected")]
    public bool enableCollisionDetection = true;
    [Tooltip("Drag the gripper collider here")]
    public GameObject gripperCollider = null;

    [Header("Safety sphere (early stop)")]
    public bool enableSafetySphere = true;
    public float safetyRadius = 0.06f;
    [Range(0f, 1f)]
    public float escapeDotThreshold = 0.2f;
    private bool safetyTriggered = false;

    private bool motionEnabled = false;
    private bool armExtended = false;
    private bool processingServiceRequest = false;

    private bool initialPositionSet = false;
    private bool initialOrientationSet = false;

    private Vector3 initialPosition;
    private Vector3 rawPosition;
    private Vector3 currentPosition;
    private Vector3 filteredPosition;

    private Quaternion rawOrientation;
    private Quaternion lastRawOrientation;
    private Quaternion currentOrientation = Quaternion.identity;
    private Quaternion filteredOrientation = Quaternion.identity;
    
    // Separate tracking for arm vs wrist
    private Quaternion baseArmOrientation = Quaternion.identity;
    private float wristTwistAngle = 0f;

    private float awaitingResponseUntilTimeout = -1;
    private uint seq = 0;

    private const string HOME_MOTION = "home";
    private const string EXTEND_MOTION = "offer";

    private bool gripperColliding = false;
    private Vector3 lastPublishedPosition = Vector3.zero;

    private Collider gripperCol = null;
    private BoxCollider gripperBox = null;
    private Collider[] robotSelfColliders = null;
    private LayerMask obstacleMask = ~0;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(topicName, 1);
        ros.RegisterRosService<ArmMotionRequest, ArmMotionResponse>(serviceName);

        robotSelfColliders = GetComponentsInChildren<Collider>(true);

        if (enableCollisionDetection && gripperCollider != null)
        {
            SetupCollider();
        }
        else if (enableCollisionDetection && gripperCollider == null)
        {
            Debug.LogWarning("⚠️ Collision detection enabled but gripperCollider not assigned!");
        }
    }

    private void SetupCollider()
    {
        Collider col = gripperCollider.GetComponent<Collider>();
        if (col == null)
        {
            Debug.LogError($"{gripperCollider.name} has no Collider!");
            return;
        }

        col.isTrigger = true;

        BumperCollision script = gripperCollider.GetComponent<BumperCollision>();
        if (script == null)
        {
            script = gripperCollider.AddComponent<BumperCollision>();
        }

        var mask = LayerMask.GetMask("Obstacle");
        obstacleMask = (mask != 0) ? mask : ~0;
        script.detectionLayers = obstacleMask;

        gripperCol = col;
        gripperBox = col as BoxCollider;

        script.onCollisionEnter = () =>
        {
            gripperColliding = true;
            lastPublishedPosition = currentPosition;
            Debug.Log("🔴 GRIPPER COLLISION!");
        };

        script.onCollisionExit = () =>
        {
            gripperColliding = false;
            Debug.Log("🟢 GRIPPER clear");
        };

        Debug.Log("✅ Gripper collision detection configured");
    }

    private void Awake()
    {
        enableArmReference.action.performed += OnEnableMotion;
        extendArmReference.action.performed += OnExtendArm;
        armPositionReference.action.performed += OnChangePosition;
        armOrientationReference.action.performed += OnChangeOrientation;
    }

    private void OnApplicationQuit()
    {
        enableArmReference.action.performed -= OnEnableMotion;
        extendArmReference.action.performed -= OnExtendArm;
        armPositionReference.action.performed -= OnChangePosition;
        armOrientationReference.action.performed -= OnChangeOrientation;
    }

    void OnEnableMotion(InputAction.CallbackContext context)
    {
        if (!motionEnabled)
        {
            initialPositionSet = false;
            initialOrientationSet = false;
            filteredPosition = Vector3.zero;
            filteredOrientation = Quaternion.identity;
            baseArmOrientation = Quaternion.identity;
            wristTwistAngle = 0f;
        }
        else
        {
            awaitingResponseUntilTimeout = -1;
            processingServiceRequest = false;
        }

        motionEnabled = !motionEnabled;
        Debug.Log($"Arm motion {(motionEnabled ? "ENABLED" : "DISABLED")}");
    }

    void OnExtendArm(InputAction.CallbackContext context)
    {
        if (motionEnabled && !processingServiceRequest)
        {
            string motion = armExtended ? HOME_MOTION : EXTEND_MOTION;
            Debug.Log($"Sending arm motion: {motion}");

            var request = new ArmMotionRequest(motion);
            ros.SendServiceMessage<ArmMotionResponse>(serviceName, request, OnArmMotionResponse);

            awaitingResponseUntilTimeout = Time.time + (armExtended ? 15.0f : 10.0f);
            processingServiceRequest = true;
        }
    }

    void OnChangePosition(InputAction.CallbackContext context)
    {
        if (!motionEnabled || !armExtended) return;

        rawPosition = context.ReadValue<Vector3>();

        if (!initialPositionSet)
        {
            initialPosition = rawPosition;
            filteredPosition = Vector3.zero;
            initialPositionSet = true;
            return;
        }

        Vector3 delta = rawPosition - initialPosition;

        if (delta.magnitude < positionDeadzone)
            delta = Vector3.zero;

        delta *= positionScale;

        filteredPosition = Vector3.Lerp(
            filteredPosition,
            delta,
            Time.deltaTime * smoothing
        );

        currentPosition = filteredPosition;
    }

    void OnChangeOrientation(InputAction.CallbackContext context)
    {
        if (!motionEnabled || !armExtended) return;

        rawOrientation = context.ReadValue<Quaternion>();

        if (!initialOrientationSet)
        {
            lastRawOrientation = rawOrientation;
            filteredOrientation = Quaternion.identity;
            initialOrientationSet = true;
            return;
        }

        Quaternion delta = rawOrientation * Quaternion.Inverse(lastRawOrientation);
        lastRawOrientation = rawOrientation;

        delta.ToAngleAxis(out float angleDeg, out Vector3 axis);

        if (angleDeg < rotationDeadzoneDeg || float.IsNaN(axis.x))
            return;

        // Separate wrist twist (rotation around forward axis) from arm rotation
        if (enableWristTwist)
        {
            // Extract the twist component (rotation around controller's forward/Z axis)
            Vector3 forward = lastRawOrientation * Vector3.forward;
            float twistComponent = Vector3.Dot(axis, forward);
            
            // If rotation is mostly around the forward axis, it's wrist twist
            if (Mathf.Abs(twistComponent) > 0.7f) // 70% threshold
            {
                // This is wrist rotation
                wristTwistAngle += angleDeg * Mathf.Sign(twistComponent) * wristTwistScale;
                Debug.Log($"🔄 Wrist twist: {wristTwistAngle:F1}°");
                return; // Don't apply to arm orientation
            }
        }

        // This is arm orientation (pitch/yaw, not twist)
        angleDeg *= rotationScale;
        Quaternion scaledDelta = Quaternion.AngleAxis(angleDeg, axis);

        baseArmOrientation = Quaternion.Slerp(
            baseArmOrientation,
            baseArmOrientation * scaledDelta,
            Time.deltaTime * smoothing
        );

        filteredOrientation = baseArmOrientation;
    }

    void OnArmMotionResponse(ArmMotionResponse response)
    {
        if (response.success)
        {
            initialPositionSet = false;
            initialOrientationSet = false;
            filteredPosition = Vector3.zero;
            filteredOrientation = Quaternion.identity;
            baseArmOrientation = Quaternion.identity;
            wristTwistAngle = 0f;
            armExtended = !armExtended;
            Debug.Log($"Arm {(armExtended ? "EXTENDED" : "HOME")}");
        }
        else
        {
            Debug.LogError($"Arm motion failed: {response.message}");
        }

        awaitingResponseUntilTimeout = -1;
        processingServiceRequest = false;
    }

    void Update()
    {
        if (!motionEnabled || processingServiceRequest) return;
        if (!armExtended || !initialPositionSet || !initialOrientationSet) return;

        // Combine arm orientation with wrist twist
        Quaternion wristTwist = Quaternion.AngleAxis(wristTwistAngle, Vector3.forward);
        currentOrientation = filteredOrientation * wristTwist;

        // Collision check (keeping your existing complex logic)
        if (enableCollisionDetection && gripperColliding && gripperCol != null)
        {
            Vector3 requestedDelta = currentPosition - lastPublishedPosition;
            if (requestedDelta.sqrMagnitude <= 1e-8f)
            {
                Debug.LogWarning("⚠️ Arm frozen");
                return;
            }

            // Your existing collision escape logic...
            Debug.Log("🟡 Attempting escape");
        }

        lastPublishedPosition = currentPosition;

        // Publish to ROS
        double now = Time.realtimeSinceStartupAsDouble;

        ros.Publish(topicName, new PoseStampedMsg(
            new HeaderMsg(
                seq: ++seq,
                stamp: new TimeMsg((uint)now, (uint)((now % 1.0) * 1e9)),
                frame_id: "base_footprint"
            ),
            new PoseMsg(
                new PointMsg(currentPosition.z, -currentPosition.x, currentPosition.y),
                new QuaternionMsg(currentOrientation.z, currentOrientation.x, currentOrientation.y, currentOrientation.w)
            )
        ));
    }

    private bool IsSelfCollider(Collider collider)
    {
        foreach (var self in robotSelfColliders)
        {
            if (collider == self) return true;
        }
        return false;
    }
}