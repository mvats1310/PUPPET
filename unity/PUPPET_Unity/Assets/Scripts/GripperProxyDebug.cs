using UnityEngine;

public class GripperProxyDebug : MonoBehaviour
{
    public Transform gripper;

    void Update()
    {
        float distance = Vector3.Distance(transform.position, gripper.position);

        if (distance > 0.02f)
        {
            Debug.Log("Collision resistance detected!");
        }
    }
}
