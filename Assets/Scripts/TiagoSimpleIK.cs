using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class TiagoSimpleIK : MonoBehaviour
{
    public Transform handTarget;         // assign your HandTarget
    public Transform[] joints;           // assign from arm_1_link → wrist_ft_tool_link
    public int iterations = 10;
    public float step = 2f;

    void LateUpdate()
    {
        if (!handTarget) return;

        // simple CCD IK
        for (int it = 0; it < iterations; it++)
        {
            for (int i = joints.Length - 2; i >= 0; i--)
            {
                Transform joint = joints[i];
                Transform end = joints[joints.Length - 1];
                Vector3 toEnd = end.position - joint.position;
                Vector3 toTarget = handTarget.position - joint.position;
                Quaternion rot = Quaternion.FromToRotation(toEnd, toTarget);
                joint.rotation = rot * joint.rotation;
            }
        }
    }
}
