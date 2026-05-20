using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class GrabbableObject : MonoBehaviour
{
    private Rigidbody rb;
    
    void Awake()
    {
        rb = GetComponent<Rigidbody>();
        
        // Ensure tag is set
        if (!CompareTag("Grabbable"))
        {
            Debug.LogWarning($"{gameObject.name} has GrabbableObject script but is not tagged as 'Grabbable'");
        }
    }
    
    // Optional: Add constraints or special behavior when grabbed
    public void OnGrabbed()
    {
        // Called when object is grabbed (if you want to add this callback)
    }
    
    public void OnReleased()
    {
        // Called when object is released (if you want to add this callback)
    }
}