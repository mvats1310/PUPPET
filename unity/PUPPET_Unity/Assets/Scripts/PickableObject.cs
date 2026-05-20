using UnityEngine;

public class PickableObject : MonoBehaviour
{
    [Header("Pickup Settings")]
    public bool isGrabbable = true;
    public bool isCurrentlyGrabbed = false;
    
    [Header("Physics")]
    public float grabReleaseForce = 2f;
    
    private Rigidbody rb;
    private Transform grabParent;
    private Vector3 originalScale;
    
    void Start()
    {
        rb = GetComponent<Rigidbody>();
        if (rb == null)
        {
            rb = gameObject.AddComponent<Rigidbody>();
        }
        
        // Setup physics properties
        rb.mass = 0.2f; // 200g cube
        rb.drag = 0.5f;
        rb.angularDrag = 0.5f;
        rb.useGravity = true;
        
        originalScale = transform.localScale;
    }
    
    public void Grab(Transform parent)
    {
        if (!isGrabbable || isCurrentlyGrabbed) return;
        
        isCurrentlyGrabbed = true;
        grabParent = parent;
        
        // Make kinematic so it follows the gripper exactly
        rb.isKinematic = true;
        rb.useGravity = false;
        
        // Parent to gripper
        transform.SetParent(parent);
        
        Debug.Log($"[PickableObject] {gameObject.name} grabbed by {parent.name}");
    }
    
    public void Release()
    {
        if (!isCurrentlyGrabbed) return;
        
        isCurrentlyGrabbed = false;
        
        // Unparent
        transform.SetParent(null);
        
        // Re-enable physics
        rb.isKinematic = false;
        rb.useGravity = true;
        
        // Add small release force for realism
        if (grabParent != null)
        {
            rb.velocity = grabParent.forward * grabReleaseForce;
        }
        
        grabParent = null;
        
        Debug.Log($"[PickableObject] {gameObject.name} released");
    }
    
    void OnDestroy()
    {
        if (isCurrentlyGrabbed)
        {
            Release();
        }
    }
}