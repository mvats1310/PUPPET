using UnityEngine;

public class GripperGrabber : MonoBehaviour
{
    [Header("Gripper State")]
    public bool gripperClosed = false;   // Set from ROS / VR input

    [Header("Grasp Settings")]
    public string grabbableTag = "Grabbable";

    private Rigidbody heldObject = null;
    private Transform heldTransform = null;
    private SphereCollider triggerCollider;

    void Awake()
    {
        triggerCollider = GetComponent<SphereCollider>();
        if (triggerCollider == null)
        {
            Debug.LogError("GripperGrabber requires a SphereCollider.");
        }
    }

    void OnTriggerEnter(Collider other)
    {
        TryGrab(other);
    }

    void Update()
    {
        // Grab if closing while already overlapping
        if (gripperClosed && heldObject == null)
        {
            Collider[] hits = Physics.OverlapSphere(
                transform.position,
                triggerCollider.radius,
                ~0,
                QueryTriggerInteraction.Ignore
            );

            foreach (var hit in hits)
            {
                TryGrab(hit);
                if (heldObject != null) break;
            }
        }

        // Release
        if (!gripperClosed && heldObject != null)
        {
            Release();
        }
    }

    // 🔑 THIS IS THE IMPORTANT PART
    void LateUpdate()
    {
        if (heldTransform != null)
        {
            heldTransform.position = transform.position;
            heldTransform.rotation = transform.rotation;
        }
    }

    void TryGrab(Collider other)
    {
        if (heldObject != null) return;
        if (!gripperClosed) return;
        if (!other.CompareTag(grabbableTag)) return;

        Rigidbody rb = other.attachedRigidbody;
        if (rb == null) return;

        Grab(rb);
    }

    void Grab(Rigidbody rb)
    {
        heldObject = rb;
        heldTransform = rb.transform;

        rb.isKinematic = true;
        rb.detectCollisions = false;

        heldTransform.SetParent(null); // IMPORTANT: do NOT rely on transform parenting
        Debug.Log("GRAB SUCCESS: " + rb.name);
    }

    void Release()
    {
        heldObject.isKinematic = false;
        heldObject.detectCollisions = true;

        heldObject = null;
        heldTransform = null;

        Debug.Log("RELEASE");
    }

    void OnDrawGizmosSelected()
    {
        if (triggerCollider != null)
        {
            Gizmos.color = Color.green;
            Gizmos.DrawWireSphere(transform.position, triggerCollider.radius);
        }
    }
}
