using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;

public class TiagoPushPublisher : MonoBehaviour
{
    [Header("ROS Settings")]
    [Tooltip("The ROS topic to publish Twist messages to (usually /mobile_base_controller/cmd_vel).")]
    public string topicName = "/mobile_base_controller/cmd_vel";

    [Header("Push Sensitivity")]
    [Tooltip("Minimum collision impulse magnitude to register as a push.")]
    public float pushThreshold = 0.05f;
    [Tooltip("Scales the impulse magnitude to linear velocity.")]
    public float velocityScale = 0.4f;
    [Tooltip("Maximum linear velocity the robot can be commanded (m/s).")]
    public float maxLinearVelocity = 0.5f;
    [Tooltip("Maximum angular velocity the robot can be commanded (rad/s).")]
    public float maxAngularVelocity = 1.0f;
    [Tooltip("Time it takes for the commanded velocity to decay back to zero (seconds).")]
    public float decayTime = 1.0f;

    // Internal State
    private ROSConnection ros;
    private Vector3 currentLinearVel = Vector3.zero;
    private float currentAngularVelZ = 0f;
    private float decayTimer = 0f;

    private const float AngularVelocityFactor = 0.5f; // Conversion factor for rotation

    void Start()
    {
        // Get the ROS connection instance and register the topic
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<TwistMsg>(topicName);

        // NOTE: Ensure your ArticulationBody on the base has these settings:
        // - Use Gravity: OFF
        // - Linear Damping: ~10 (High damping is good for teleoperation)
        // - Angular Damping: ~10
    }

    // Called on the frame a collision occurs
    void OnCollisionEnter(Collision collision)
    {
        HandleCollision(collision);
    }

    // Called during the frames a collision is sustained
    void OnCollisionStay(Collision collision)
    {
        HandleCollision(collision);
    }

    void HandleCollision(Collision collision)
    {
        Vector3 impulse = collision.impulse;
        float magnitude = impulse.magnitude;

        if (magnitude < pushThreshold) return;

        // --- 1. Calculate Linear Velocity (Forward/Backward) ---
        // Impulse in Unity Z-axis (forward/backward) is mapped to linear.x in ROS Twist
        float linearZ = impulse.z;
        currentLinearVel.x = linearZ * velocityScale;
        currentLinearVel.x = Mathf.Clamp(currentLinearVel.x, -maxLinearVelocity, maxLinearVelocity);

        // --- 2. Calculate Angular Velocity (Rotation/Yaw) ---
        // Impulse in Unity X-axis (side-to-side) generates angular velocity (rotation/yaw)
        // We use the lateral (X) component of the impulse for rotation (Yaw)
        float angularX = impulse.x;
        currentAngularVelZ = -angularX * AngularVelocityFactor * velocityScale;
        currentAngularVelZ = Mathf.Clamp(currentAngularVelZ, -maxAngularVelocity, maxAngularVelocity);

        // Reset the decay timer to restart the velocity decay process
        decayTimer = decayTime;

        // Publish the initial velocity immediately
        PublishVelocity(currentLinearVel.x, currentAngularVelZ);
        
        // Debugging output for verification
        Debug.Log($"Impulse Mag: {magnitude:F2} → Linear X: {currentLinearVel.x:F2}, Angular Z: {currentAngularVelZ:F2}");
    }

    void Update()
    {
        // Handle velocity decay and continuous publishing
        if (decayTimer > 0f)
        {
            decayTimer -= Time.deltaTime;
            
            // Calculate the decay factor (1.0 = full velocity, 0.0 = zero velocity)
            float decayFactor = decayTimer / decayTime; 

            // Interpolate the current commanded velocity from the last impulse
            float smoothLinearX = currentLinearVel.x * decayFactor;
            float smoothAngularZ = currentAngularVelZ * decayFactor;

            PublishVelocity(smoothLinearX, smoothAngularZ);
        }
        else if (decayTimer > -Time.deltaTime) // Publish a final zero velocity once
        {
            // IMPORTANT: Explicitly send a zero velocity to the ROS controller
            // to ensure the real robot stops cleanly.
            PublishVelocity(0f, 0f);
            
            // Mark the timer as negative to prevent this block from running every frame
            decayTimer = -Time.deltaTime; 
            
            // Clear the stored velocity state for the next push
            currentLinearVel = Vector3.zero;
            currentAngularVelZ = 0f;
        }
    }

    void PublishVelocity(float linearX, float angularZ)
    {
        // Create the Twist message
        var twist = new TwistMsg
        {
            // Linear velocity is applied along the ROS X-axis (forward)
            linear = new Vector3Msg(linearX, 0.0, 0.0),
            // Angular velocity is applied around the ROS Z-axis (Yaw)
            angular = new Vector3Msg(0.0, 0.0, angularZ)
        };
        
        // Publish the command
        ros.Publish(topicName, twist);
    }
}