using UnityEngine;
using UnityEngine.InputSystem;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;

public class GripperCommander : MonoBehaviour
{
    private ROSConnection ros;

    [Header("Input")]
    public InputActionReference triggerReference = null;
    public InputActionReference squeezeReference = null;

    [Header("ROS")]
    public string topicName = "/gripper_tp_controller/command";
    public float publishMessageFrequency = 0.02f;

    private bool triggering;
    private bool squeezing;
    private float timeElapsed;

    [Header("Tuning")]
    public int openStep = 10;
    public int closeStep = 10;
    public bool sendMagnitude = true;
    public float openMultiplier = 2.0f;

    [Header("Grabbing")]
    public Transform gripperTransform;   // MyColliderGripper
    public float grabRadius = 0.03f;
    public string grabbableTag = "Grabbable";

    private GameObject attachedObject = null;
    private Rigidbody attachedRigidbody = null;
    private bool isGripperClosed = false;
    
    // Store original position offset when grabbed
    private Vector3 grabOffset;
    private Quaternion grabRotationOffset;

    private void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<Int32Msg>(topicName);

        if (gripperTransform == null)
            gripperTransform = transform;
    }

    private void Awake()
    {
        triggerReference.action.performed += _ => triggering = true;
        triggerReference.action.canceled += _ => triggering = false;

        squeezeReference.action.performed += _ => squeezing = true;
        squeezeReference.action.canceled += _ => squeezing = false;
    }

    void Update()
    {
        if (triggering ^ squeezing)
        {
            timeElapsed += Time.deltaTime;

            if (timeElapsed > publishMessageFrequency)
            {
                int cmd;

                if (sendMagnitude)
                {
                    int step = triggering
                        ? Mathf.Max(1, Mathf.RoundToInt(openStep * openMultiplier))
                        : closeStep;

                    cmd = (triggering ? 1 : -1) * step;
                }
                else
                {
                    cmd = triggering ? 1 : -1;
                }

                ros.Publish(topicName, new Int32Msg(cmd));

                // GRAB LOGIC
                if (squeezing && !isGripperClosed)
                {
                    isGripperClosed = true;

                    if (attachedObject == null)
                        AttachTouchingObject();
                }
                else if (triggering && isGripperClosed)
                {
                    isGripperClosed = false;

                    if (attachedObject != null)
                        ReleaseObject();
                }

                timeElapsed = 0;
            }
        }

        // Keep object following gripper smoothly while attached
        if (attachedObject != null && attachedRigidbody != null && attachedRigidbody.isKinematic)
        {
            // Smoothly follow gripper position
            Vector3 targetPos = gripperTransform.position + gripperTransform.TransformDirection(grabOffset);
            Quaternion targetRot = gripperTransform.rotation * grabRotationOffset;
            
            attachedObject.transform.position = Vector3.Lerp(
                attachedObject.transform.position, 
                targetPos, 
                Time.deltaTime * 20f  // Smooth follow
            );
            
            attachedObject.transform.rotation = Quaternion.Slerp(
                attachedObject.transform.rotation,
                targetRot,
                Time.deltaTime * 20f
            );
        }
    }

    void AttachTouchingObject()
    {
        Debug.Log("Attempting to grab object...");

        Collider[] colliders = Physics.OverlapSphere(gripperTransform.position, grabRadius);

        foreach (var collider in colliders)
        {
            // Skip gripper itself and its children
            if (collider.transform == gripperTransform ||
                collider.transform.IsChildOf(gripperTransform))
                continue;

            if (collider.CompareTag(grabbableTag))
            {
                attachedObject = collider.gameObject;
                attachedRigidbody = collider.attachedRigidbody;

                if (attachedRigidbody != null)
                {
                    // Store the OFFSET from gripper when grabbed (don't snap!)
                    grabOffset = gripperTransform.InverseTransformDirection(
                        attachedObject.transform.position - gripperTransform.position
                    );
                    grabRotationOffset = Quaternion.Inverse(gripperTransform.rotation) * attachedObject.transform.rotation;

                    // Stop all motion immediately
                    attachedRigidbody.velocity = Vector3.zero;
                    attachedRigidbody.angularVelocity = Vector3.zero;

                    // Make kinematic so it doesn't fall or react to physics
                    attachedRigidbody.isKinematic = true;
                    
                    // Increase drag to prevent sliding
                    attachedRigidbody.drag = 10f;
                    attachedRigidbody.angularDrag = 10f;

                    Debug.Log($"✅ GRABBED: {attachedObject.name} at offset {grabOffset}");
                }
                else
                {
                    Debug.LogWarning($"Object {attachedObject.name} has no Rigidbody!");
                    attachedObject = null;
                }

                break;
            }
        }
    }

    void ReleaseObject()
    {
        if (attachedObject != null)
        {
            Debug.Log($"✅ RELEASED: {attachedObject.name}");

            // Re-enable physics
            if (attachedRigidbody != null)
            {
                attachedRigidbody.isKinematic = false;
                
                // Reset drag to normal
                attachedRigidbody.drag = 0f;
                attachedRigidbody.angularDrag = 0.05f;
                
                // Apply small downward velocity for natural drop
                attachedRigidbody.velocity = Vector3.down * 0.1f;
            }

            attachedObject = null;
            attachedRigidbody = null;
        }
    }

    private void OnDrawGizmosSelected()
    {
        if (gripperTransform != null)
        {
            Gizmos.color = isGripperClosed ? Color.green : Color.yellow;
            Gizmos.DrawWireSphere(gripperTransform.position, grabRadius);
        }
    }
}