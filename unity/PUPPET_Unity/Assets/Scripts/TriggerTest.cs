using UnityEngine;

public class TriggerTest : MonoBehaviour
{
    private void Start()
    {
        Collider col = GetComponent<Collider>();
        Debug.Log($"=== TRIGGER TEST on {gameObject.name} ===");
        Debug.Log($"Has Collider: {col != null}");
        Debug.Log($"Is Trigger: {col?.isTrigger}");
        Debug.Log($"Layer: {LayerMask.LayerToName(gameObject.layer)}");
        
        Rigidbody rb = GetComponent<Rigidbody>();
        Debug.Log($"Has Rigidbody: {rb != null}");
        if (rb != null)
        {
            Debug.Log($"Is Kinematic: {rb.isKinematic}");
        }
    }

    private void OnTriggerEnter(Collider other)
    {
        // Log EVERYTHING - no filtering
        Debug.Log($"🚨 TRIGGER ENTER: {gameObject.name} touched {other.gameObject.name} | Layer: {LayerMask.LayerToName(other.gameObject.layer)} | IsTrigger: {other.isTrigger}");
    }

    private void OnTriggerStay(Collider other)
    {
        Debug.Log($"🔄 TRIGGER STAY: {gameObject.name} still touching {other.gameObject.name}");
    }

    private void OnTriggerExit(Collider other)
    {
        Debug.Log($"✅ TRIGGER EXIT: {gameObject.name} left {other.gameObject.name}");
    }

    private void OnCollisionEnter(Collision other)
    {
        Debug.Log($"💥 COLLISION ENTER: {gameObject.name} collided with {other.gameObject.name}");
    }
}