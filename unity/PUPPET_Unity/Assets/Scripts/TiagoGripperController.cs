using UnityEngine;
using System.Collections.Generic;

public class TiagoGripperController : MonoBehaviour
{
    [Header("Gripper References")]
    [Tooltip("The transform between the two gripper fingers (usually gripper_grasping_frame)")]
    public Transform gripperCenter;
    
    [Header("Grip Detection")]
    public float gripThreshold = 0.02f;
    public float releaseThreshold = 0.07f;
    
    [Header("Pickup Settings")]
    public LayerMask pickupLayer = -1; // Everything by default
    public float detectionRadius = 0.15f; // Increased to 15cm for easier testing
    
    [Header("Debug")]
    public bool showDebug = true;
    public bool listAllGripperTransforms = false;
    
    private PickableObject currentObject;
    private bool wasGripping = false;
    private Transform leftFinger;
    private Transform rightFinger;
    
    void Start()
    {
        leftFinger = FindDeepChild(transform.root, "gripper_left_finger_joint");
        rightFinger = FindDeepChild(transform.root, "gripper_right_finger_joint");
        
        if (leftFinger == null)
            Debug.LogWarning("[TiagoGripperController] Left finger not found!");
        if (rightFinger == null)
            Debug.LogWarning("[TiagoGripperController] Right finger not found!");
        
        if (gripperCenter == null)
        {
            var candidates = new string[] 
            { 
                "gripper_grasping_frame",
                "gripper_tool_link",
                "gripper_link",
                "wrist_ft_tool_link",
                "gripper_base_link"
            };
            
            foreach (var name in candidates)
            {
                var found = FindDeepChild(transform.root, name);
                if (found != null)
                {
                    gripperCenter = found;
                    Debug.Log($"[TiagoGripperController] ✓ Auto-found gripper center: {name}");
                    break;
                }
            }
            
            if (gripperCenter == null && leftFinger != null && rightFinger != null)
            {
                GameObject centerObj = new GameObject("GripperCenterCalculated");
                centerObj.transform.SetParent(leftFinger.parent);
                gripperCenter = centerObj.transform;
                Debug.Log("[TiagoGripperController] ✓ Created calculated gripper center");
            }
        }
        else
        {
            Debug.Log($"[TiagoGripperController] ✓ Using assigned gripper center: {gripperCenter.name}");
        }
        
        if (gripperCenter == null)
        {
            Debug.LogError("[TiagoGripperController] ❌ Gripper center not found!");
        }
        
        if (listAllGripperTransforms)
        {
            Debug.Log("=== All Gripper Transforms ===");
            foreach (Transform t in transform.root.GetComponentsInChildren<Transform>())
            {
                if (t.name.ToLower().Contains("gripper") || t.name.ToLower().Contains("wrist"))
                {
                    Debug.Log($"  • {GetTransformPath(t)}");
                }
            }
            Debug.Log("==============================");
        }
        
        // Find and log all PickableObjects in scene
        var pickables = FindObjectsOfType<PickableObject>();
        Debug.Log($"[TiagoGripperController] Found {pickables.Length} PickableObject(s) in scene:");
        foreach (var p in pickables)
        {
            Debug.Log($"  • {p.name} at position {p.transform.position}");
        }
    }
    
    void Update()
    {
        if (gripperCenter == null) return;
        
        if (gripperCenter.name == "GripperCenterCalculated" && leftFinger != null && rightFinger != null)
        {
            gripperCenter.position = (leftFinger.position + rightFinger.position) / 2f;
            gripperCenter.rotation = leftFinger.rotation;
        }
        
        float gripDistance = GetGripDistance();
        bool isGripping = gripDistance < gripThreshold;
        
        // Grip state changed from open to closed - try to grab
        if (isGripping && !wasGripping)
        {
            Debug.Log($"[TiagoGripperController] 🤏 Gripper CLOSED (distance: {gripDistance:F4}m) - attempting grab...");
            Debug.Log($"[TiagoGripperController] Gripper center position: {gripperCenter.position}");
            TryGrabObject();
        }
        // Grip state changed from closed to open - release
        else if (!isGripping && wasGripping && gripDistance > releaseThreshold)
        {
            Debug.Log($"[TiagoGripperController] ✋ Gripper OPENED (distance: {gripDistance:F4}m) - releasing...");
            ReleaseObject();
        }
        
        wasGripping = isGripping;
        
        if (showDebug)
        {
            DrawDebugInfo(gripDistance, isGripping);
        }
    }
    
    float GetGripDistance()
    {
        if (leftFinger == null || rightFinger == null)
            return float.MaxValue;
        
        return Vector3.Distance(leftFinger.position, rightFinger.position);
    }
    
    void TryGrabObject()
    {
        if (currentObject != null)
        {
            Debug.Log("[TiagoGripperController] Already holding an object");
            return;
        }
        
        // Log what we're searching for
        Debug.Log($"[TiagoGripperController] 🔍 Searching sphere:");
        Debug.Log($"  Position: {gripperCenter.position}");
        Debug.Log($"  Radius: {detectionRadius}m");
        Debug.Log($"  Layer Mask: {pickupLayer.value}");
        
        // Check for ALL colliders first (no layer mask)
        Collider[] allColliders = Physics.OverlapSphere(gripperCenter.position, detectionRadius);
        Debug.Log($"[TiagoGripperController] Found {allColliders.Length} total colliders (all layers):");
        foreach (var col in allColliders)
        {
            float dist = Vector3.Distance(gripperCenter.position, col.transform.position);
            Debug.Log($"  • {col.name} (Layer: {LayerMask.LayerToName(col.gameObject.layer)}) at {dist:F3}m");
        }
        
        // Now check with layer mask
        Collider[] colliders = Physics.OverlapSphere(
            gripperCenter.position, 
            detectionRadius, 
            pickupLayer
        );
        
        Debug.Log($"[TiagoGripperController] Found {colliders.Length} colliders (with layer mask)");
        
        PickableObject closestObject = null;
        float closestDistance = float.MaxValue;
        
        foreach (var col in colliders)
        {
            Debug.Log($"[TiagoGripperController] Checking: {col.name}");
            
            // Skip if it's part of the robot itself
            if (col.transform.IsChildOf(transform.root))
            {
                Debug.Log($"[TiagoGripperController]   ↳ SKIPPED (robot part)");
                continue;
            }
            
            var pickable = col.GetComponent<PickableObject>();
            if (pickable != null)
            {
                Debug.Log($"[TiagoGripperController]   ↳ Has PickableObject: grabbable={pickable.isGrabbable}, grabbed={pickable.isCurrentlyGrabbed}");
                
                if (pickable.isGrabbable && !pickable.isCurrentlyGrabbed)
                {
                    float distance = Vector3.Distance(gripperCenter.position, col.transform.position);
                    Debug.Log($"[TiagoGripperController]   ↳ VALID! Distance: {distance:F3}m");
                    
                    if (distance < closestDistance)
                    {
                        closestDistance = distance;
                        closestObject = pickable;
                    }
                }
            }
            else
            {
                Debug.Log($"[TiagoGripperController]   ↳ NO PickableObject component!");
            }
        }
        
        if (closestObject != null)
        {
            currentObject = closestObject;
            currentObject.Grab(gripperCenter);
            Debug.Log($"[TiagoGripperController] ✅✅✅ GRABBED: {currentObject.name} ✅✅✅");
        }
        else
        {
            Debug.Log("[TiagoGripperController] ❌ No pickable objects found in range");
        }
    }
    
    void ReleaseObject()
    {
        if (currentObject != null)
        {
            Debug.Log($"[TiagoGripperController] ✅ RELEASED: {currentObject.name}");
            currentObject.Release();
            currentObject = null;
        }
    }
    
    void DrawDebugInfo(float gripDistance, bool isGripping)
    {
        if (gripperCenter != null)
        {
            Color sphereColor = isGripping ? Color.green : Color.yellow;
            if (currentObject != null) sphereColor = Color.cyan;
            
            Debug.DrawRay(gripperCenter.position, Vector3.up * detectionRadius, sphereColor);
            Debug.DrawRay(gripperCenter.position, Vector3.down * detectionRadius, sphereColor);
            Debug.DrawRay(gripperCenter.position, Vector3.left * detectionRadius, sphereColor);
            Debug.DrawRay(gripperCenter.position, Vector3.right * detectionRadius, sphereColor);
            Debug.DrawRay(gripperCenter.position, Vector3.forward * detectionRadius, sphereColor);
            Debug.DrawRay(gripperCenter.position, Vector3.back * detectionRadius, sphereColor);
        }
        
        if (leftFinger != null && rightFinger != null)
        {
            Debug.DrawLine(leftFinger.position, rightFinger.position, 
                isGripping ? Color.red : Color.green);
        }
    }
    
    Transform FindDeepChild(Transform parent, string name)
    {
        foreach (Transform child in parent.GetComponentsInChildren<Transform>(true))
        {
            if (child.name == name)
                return child;
        }
        return null;
    }
    
    string GetTransformPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null)
        {
            t = t.parent;
            path = t.name + "/" + path;
        }
        return path;
    }
    
    void OnDrawGizmos()
    {
        if (gripperCenter != null && showDebug)
        {
            Gizmos.color = currentObject != null ? Color.cyan : Color.yellow;
            Gizmos.DrawWireSphere(gripperCenter.position, detectionRadius);
            
            if (leftFinger != null)
            {
                Gizmos.color = Color.blue;
                Gizmos.DrawSphere(leftFinger.position, 0.01f);
            }
            if (rightFinger != null)
            {
                Gizmos.color = Color.red;
                Gizmos.DrawSphere(rightFinger.position, 0.01f);
            }
        }
    }
}