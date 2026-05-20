using UnityEngine;
using System;

public class BumperCollision : MonoBehaviour
{
    public Action onCollisionEnter;
    public Action onCollisionExit;

    [Tooltip("Tag to detect collisions with (leave empty to detect all objects)")]
    public string obstacleTag = "";
    
    [Tooltip("Layer mask - only detect these layers")]
    public LayerMask detectionLayers = ~0; // Default: everything

    private int collisionCount = 0;

    private void Start()
    {
        // Verify setup
        Collider col = GetComponent<Collider>();
        if (col == null)
        {
            Debug.LogError($"{gameObject.name} has NO COLLIDER!");
        }
        else if (!col.isTrigger)
        {
            Debug.LogError($"{gameObject.name} collider is NOT set as trigger!");
        }
        else
        {
            Debug.Log($"✅ {gameObject.name} configured: {col.GetType().Name}, IsTrigger={col.isTrigger}");
        }

        // Check for rigidbody
        Rigidbody rb = GetComponent<Rigidbody>();
        if (rb != null)
        {
            Debug.LogError($" {gameObject.name} has a Rigidbody! Remove it!");
        }
        
        Debug.Log($"  Detection layers: {LayerMaskToString(detectionLayers)}");
    }

    private void OnTriggerEnter(Collider other)
    {
        // CHECK LAYER FIRST - ignore if not in detection layers
        if ((detectionLayers.value & (1 << other.gameObject.layer)) == 0)
        {
            Debug.Log($"[{gameObject.name}] Ignoring {other.gameObject.name} - wrong layer ({LayerMask.LayerToName(other.gameObject.layer)})");
            return;
        }

        Debug.Log($"[{gameObject.name}] Trigger by: {other.gameObject.name} (Layer: {LayerMask.LayerToName(other.gameObject.layer)}, Tag: {other.tag})");

        // Check tag filter
        if (!string.IsNullOrEmpty(obstacleTag) && !other.CompareTag(obstacleTag))
        {
            Debug.Log($"  → Ignoring: wrong tag");
            return;
        }

        // Ignore other triggers
        if (other.isTrigger)
        {
            Debug.Log($"  → Ignoring: is trigger");
            return;
        }

        collisionCount++;
        
        if (collisionCount == 1)
        {
            Debug.Log($" {gameObject.name} CONTACT: {other.gameObject.name}");
            onCollisionEnter?.Invoke();
        }
    }

    private void OnTriggerExit(Collider other)
    {
        // CHECK LAYER FIRST
        if ((detectionLayers.value & (1 << other.gameObject.layer)) == 0)
        {
            return;
        }

        // Check tag filter
        if (!string.IsNullOrEmpty(obstacleTag) && !other.CompareTag(obstacleTag))
        {
            return;
        }

        // Ignore triggers
        if (other.isTrigger)
        {
            return;
        }

        collisionCount = Mathf.Max(0, collisionCount - 1);
        
        if (collisionCount == 0)
        {
            Debug.Log($" {gameObject.name} CLEAR");
            onCollisionExit?.Invoke();
        }
    }

    private string LayerMaskToString(LayerMask mask)
    {
        string result = "";
        for (int i = 0; i < 32; i++)
        {
            if ((mask.value & (1 << i)) != 0)
            {
                if (result.Length > 0) result += ", ";
                result += LayerMask.LayerToName(i);
            }
        }
        return result;
    }

    private void OnDrawGizmos()
    {
        Collider col = GetComponent<Collider>();
        if (col != null)
        {
            Gizmos.color = collisionCount > 0 ? Color.red : Color.green;
            Gizmos.matrix = transform.localToWorldMatrix;
            
            if (col is BoxCollider box)
            {
                Gizmos.DrawWireCube(box.center, box.size);
            }
            else if (col is SphereCollider sphere)
            {
                Gizmos.DrawWireSphere(sphere.center, sphere.radius);
            }
        }
    }
}