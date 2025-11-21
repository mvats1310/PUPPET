using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class TiagoArmFollower : MonoBehaviour
{
    [Header("References")]
    public Transform vrHand;          // Your VR controller (RightHand)
    public Transform endEffector;     // Tiago's gripper_link
    public float followSpeed = 2.0f;  // How fast the arm adjusts
    public float reachThreshold = 0.01f; // Stop moving when close enough

    void Update()
    {
        if (vrHand == null || endEffector == null)
            return;

        // Calculate desired position and rotation
        Vector3 targetPos = vrHand.position;
        Quaternion targetRot = vrHand.rotation;

        // Smooth movement toward target
        endEffector.position = Vector3.Lerp(endEffector.position, targetPos, Time.deltaTime * followSpeed);
        endEffector.rotation = Quaternion.Slerp(endEffector.rotation, targetRot, Time.deltaTime * followSpeed);
    }
}

