using UnityEngine;

public class DisablePhysicsOnStart : MonoBehaviour
{
    void Awake()
    {
        // Disable all ArticulationBodies so they don't fight your movement
        foreach (var ab in GetComponentsInChildren<ArticulationBody>())
        {
            ab.enabled = false;
        }
    }
}
