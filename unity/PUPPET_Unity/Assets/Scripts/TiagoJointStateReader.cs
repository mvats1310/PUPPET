using System;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;

public class TiagoJointStateSubscriber : MonoBehaviour
{
    // ============================================================
    // ROS
    // ============================================================
    [Header("ROS Settings")]
    public string topicName = "/joint_states";

    [Header("Physics Interaction")]
    [Tooltip("If true, keep colliders enabled so the VR robot can physically push objects while telepresence is running")]
    public bool preservePhysics = true;
    [Tooltip("If true, disable gravity on ArticulationBody components to avoid the model falling over")]
    public bool disableGravityOnArticulation = true;

    [Header("Enforcement")]
    [Tooltip("If true, periodically re-enable colliders / physics to prevent other scripts from disabling them")]
    public bool enforcePhysics = true;
    [Tooltip("How often (s) to re-apply collider/physics settings")]
    public float enforceInterval = 0.5f;

    // ============================================================
    // SMOOTHING
    // ============================================================
    [Header("Smoothing")]
    public bool enableSmoothing = true;
    [Range(1f, 30f)]
    public float smoothingSpeed = 12f;

    // ============================================================
    // DEBUG
    // ============================================================
    [Header("Debug")]
    public bool debugMode = false;

    private ROSConnection ros;

    private Dictionary<string, Transform> jointMap = new();
    private Dictionary<string, ArticulationBody> articulationMap = new();

    private Dictionary<string, float> jointValues = new();
    private Dictionary<string, float> targetValues = new();
    private Dictionary<string, Quaternion> initialRots = new();
    private Dictionary<string, Vector3> initialPos = new();

    // Cached components for enforcement
    private Collider[] selfColliders;
    private ArticulationBody[] selfArticulations;
    private Rigidbody[] selfRigidbodies;
    private float enforceTimer = 0f;

    private float lastMessageTime;
    private const float MESSAGE_TIMEOUT = 0.5f;

    // ============================================================
    // REVOLUTE JOINT AXES (LOCAL)
    // ============================================================
    private readonly Dictionary<string, Vector3> revoluteAxes = new()
    {
        { "arm_1_joint", Vector3.up },
        { "arm_2_joint", Vector3.down },
        { "arm_3_joint", Vector3.down },
        { "arm_4_joint", Vector3.up },
        { "arm_5_joint", Vector3.up },
        { "arm_6_joint", Vector3.up },
        { "arm_7_joint", Vector3.up },
        { "head_1_joint", Vector3.up },
        { "head_2_joint", Vector3.up },
        { "gripper_left_finger_joint", Vector3.right },
        { "gripper_right_finger_joint", Vector3.right }
    };

    // ============================================================
    // SIGN CORRECTIONS
    // ============================================================
    private readonly Dictionary<string, float> sign = new()
    {
        { "arm_1_joint", -1f },
        { "arm_2_joint",  1f },
        { "arm_3_joint",  1f },
        { "arm_4_joint", -1f },
        { "arm_5_joint", -1f },
        { "arm_6_joint", -1f },
        { "arm_7_joint", -1f },
        { "head_1_joint", -1f }, // CHANGED: was 1f, now -1f to fix reversed pan
        { "head_2_joint", -1f },
        { "gripper_left_finger_joint",  1f },
        { "gripper_right_finger_joint", -1f }
    };

    // ============================================================
    // GRIPPER TUNING
    // ============================================================
    [Header("Gripper finger tuning")]
    [Tooltip("Multiply left gripper finger angle (deg). >1 makes left go up more.")]
    public float gripperLeftScale = 3.5f;
    [Tooltip("Extra degrees added to left gripper finger (deg).")]
    public float gripperLeftOffsetDeg = 0f;
    [Tooltip("Multiply right gripper finger angle (deg). >1 makes right go down more.")]
    public float gripperRightScale = 3.5f;
    [Tooltip("Extra degrees added to right gripper finger (deg).")]
    public float gripperRightOffsetDeg = 0f;

    // ============================================================
    // INIT
    // ============================================================
    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<JointStateMsg>(topicName, JointStateCallback);

        // Cache own components
        selfColliders = GetComponentsInChildren<Collider>(true);
        selfArticulations = GetComponentsInChildren<ArticulationBody>(true);
        selfRigidbodies = GetComponentsInChildren<Rigidbody>(true);

        // Preserve physics settings
        if (preservePhysics)
        {
            foreach (var c in selfColliders) if (c != null) c.enabled = true;

            if (disableGravityOnArticulation)
            {
                foreach (var a in selfArticulations)
                {
                    if (a == null) continue;
                    var type = a.GetType();
                    var useGravityProp = type.GetProperty("useGravity", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                    if (useGravityProp != null && useGravityProp.CanWrite)
                    {
                        useGravityProp.SetValue(a, false);
                        continue;
                    }
                    var gravityScaleProp = type.GetProperty("gravityScale", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                    if (gravityScaleProp != null && gravityScaleProp.CanWrite)
                    {
                        gravityScaleProp.SetValue(a, 0f);
                        continue;
                    }
                    var rb = a.GetComponent<Rigidbody>();
                    if (rb != null) rb.useGravity = false;
                }
            }
        }

        // Initialize joint mappings
        foreach (Transform t in GetComponentsInChildren<Transform>())
        {
            jointMap[t.name] = t;
            var ab = t.GetComponent<ArticulationBody>();
            if (ab != null) articulationMap[t.name] = ab;

            initialRots[t.name] = t.localRotation;
            initialPos[t.name] = t.localPosition;

            if (revoluteAxes.ContainsKey(t.name) || t.name == "torso_lift_joint")
            {
                jointValues[t.name] = 0f;
                targetValues[t.name] = 0f;
            }
        }

        if (debugMode)
            Debug.Log("[TiagoJointStateSubscriber] Initialized.");
    }

    // ============================================================
    // ROS CALLBACK
    // ============================================================
    void JointStateCallback(JointStateMsg msg)
    {
        if (msg?.name == null || msg?.position == null) return;

        lastMessageTime = Time.time;
        int n = Mathf.Min(msg.name.Length, msg.position.Length);

        if (debugMode)
        {
            Debug.Log($"[TiagoJointStateSubscriber] Received JointState with {msg.name.Length} names");
        }

        for (int i = 0; i < n; i++)
        {
            string name = msg.name[i];
            float value = (float)msg.position[i];

            if (float.IsNaN(value) || float.IsInfinity(value)) continue;

            if (debugMode && !jointMap.ContainsKey(name))
            {
                Debug.LogWarning($"[TiagoJointStateSubscriber] Incoming joint '{name}' not found in Unity hierarchy.");
            }

            // torso (prismatic)
            if (name == "torso_lift_joint")
            {
                targetValues[name] = value;
                continue;
            }

            // revolute joints (including gripper fingers)
            if (revoluteAxes.ContainsKey(name))
            {
                float deg = value * Mathf.Rad2Deg * sign[name];
                
                // Apply gripper tuning
                if (name == "gripper_left_finger_joint")
                {
                    deg = deg * gripperLeftScale + gripperLeftOffsetDeg;
                }
                else if (name == "gripper_right_finger_joint")
                {
                    deg = deg * gripperRightScale + gripperRightOffsetDeg;
                }
                
                targetValues[name] = deg;

                if (debugMode && (name.Contains("gripper") || name.Contains("finger")))
                    Debug.Log($"[TiagoJointStateSubscriber] gripper '{name}' -> {targetValues[name]:F2} deg");
            }
        }
    }

    // ============================================================
    // UPDATE
    // ============================================================
    void Update()
    {
        if (Time.time - lastMessageTime > MESSAGE_TIMEOUT)
            return;

        // Periodically enforce colliders/physics settings
        if (enforcePhysics)
        {
            enforceTimer += Time.deltaTime;
            if (enforceTimer >= enforceInterval)
            {
                enforceTimer = 0f;

                foreach (var c in selfColliders) if (c != null && !c.enabled) c.enabled = true;

                foreach (var rb in selfRigidbodies)
                {
                    if (rb == null) continue;
                    rb.isKinematic = false;
                    rb.useGravity = false;
                }

                foreach (var a in selfArticulations)
                {
                    if (a == null) continue;
                    var type = a.GetType();
                    var useGravityProp = type.GetProperty("useGravity", BindingFlags.Public | BindingFlags.Instance);
                    if (useGravityProp != null && useGravityProp.CanWrite)
                    {
                        var cur = (bool)useGravityProp.GetValue(a);
                        if (cur) useGravityProp.SetValue(a, false);
                        continue;
                    }
                    var gravityScaleProp = type.GetProperty("gravityScale", BindingFlags.Public | BindingFlags.Instance);
                    if (gravityScaleProp != null && gravityScaleProp.CanWrite)
                    {
                        var curf = (float)gravityScaleProp.GetValue(a);
                        if (curf != 0f) gravityScaleProp.SetValue(a, 0f);
                        continue;
                    }
                    var rb = a.GetComponent<Rigidbody>();
                    if (rb != null)
                    {
                        if (rb.isKinematic) rb.isKinematic = false;
                        if (rb.useGravity) rb.useGravity = false;
                    }
                }
            }
        }

        // Smooth joint values
        if (enableSmoothing)
        {
            foreach (var k in targetValues.Keys)
            {
                // Apply smoothing for most joints but let gripper fingers follow immediately
                if (k.Contains("gripper") || k.Contains("finger"))
                {
                    jointValues[k] = targetValues[k];
                }
                else
                {
                    jointValues[k] = Mathf.Lerp(jointValues[k], targetValues[k], Time.deltaTime * smoothingSpeed);
                }
            }
        }
        else
        {
            foreach (var k in targetValues.Keys)
                jointValues[k] = targetValues[k];
        }

        // Apply joint values
        foreach (var kvp in jointValues)
        {
            string name = kvp.Key;
            float value = kvp.Value;

            if (!jointMap.ContainsKey(name)) continue;
            Transform joint = jointMap[name];

            // Prefer ArticulationBody drive if available
            if (articulationMap.TryGetValue(name, out var ab))
            {
                ApplyToArticulation(ab, name, value);
                continue;
            }

            // Fallback: Transform-only
            if (name == "torso_lift_joint")
            {
                joint.localPosition = initialPos[name] + Vector3.up * value;
                continue;
            }
            if (revoluteAxes.ContainsKey(name))
            {
                joint.localRotation =
                    initialRots[name] *
                    Quaternion.AngleAxis(value, revoluteAxes[name]);
            }
        }

        // Visual fallback for gripper fingers
        string leftName = "gripper_left_finger_joint";
        string rightName = "gripper_right_finger_joint";
        if (jointMap.ContainsKey(leftName) && revoluteAxes.ContainsKey(leftName) && jointValues.ContainsKey(leftName))
        {
            jointMap[leftName].localRotation = initialRots[leftName] * Quaternion.AngleAxis(jointValues[leftName], revoluteAxes[leftName]);
        }
        if (jointMap.ContainsKey(rightName) && revoluteAxes.ContainsKey(rightName) && jointValues.ContainsKey(rightName))
        {
            jointMap[rightName].localRotation = initialRots[rightName] * Quaternion.AngleAxis(jointValues[rightName], revoluteAxes[rightName]);
        }

        if (debugMode && lastMessageTime == Time.time)
        {
            var keys = string.Join(", ", jointMap.Keys);
            Debug.Log($"[TiagoJointStateSubscriber] Unity joints: {jointMap.Count}. Sample: {(keys.Length > 200 ? keys.Substring(0, 200) + "..." : keys)}");
        }
    }

    void OnDestroy()
    {
        if (ros != null)
            ros.Unsubscribe(topicName);
    }

    void ApplyToArticulation(ArticulationBody ab, string jointName, float targetValue)
    {
        try
        {
            var driveProp = ab.GetType().GetProperty("xDrive") ??
                            ab.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance)
                               .FirstOrDefault(p => p.Name.EndsWith("Drive"));

            if (driveProp != null)
            {
                var driveObj = driveProp.GetValue(ab);
                var driveType = driveObj != null ? driveObj.GetType() : driveProp.PropertyType;
                var targetProp = driveType.GetProperty("target", BindingFlags.Public | BindingFlags.Instance);
                if (targetProp != null && targetProp.CanWrite)
                {
                    object newDrive = driveObj ?? Activator.CreateInstance(driveType);
                    targetProp.SetValue(newDrive, targetValue);
                    driveProp.SetValue(ab, newDrive);
                    return;
                }
            }
        }
        catch (Exception ex)
        {
            if (debugMode) Debug.LogWarning($"[TiagoJointStateSubscriber] Drive reflection failed for '{jointName}': {ex.Message}");
        }

        // Final fallback: visual transform
        if (jointName == "torso_lift_joint")
        {
            ab.transform.localPosition = initialPos[jointName] + Vector3.up * targetValue;
        }
        else if (revoluteAxes.ContainsKey(jointName))
        {
            ab.transform.localRotation = initialRots[jointName] * Quaternion.AngleAxis(targetValue, revoluteAxes[jointName]);
        }
    }
}