using UnityEngine;

public class TiagoExactHomePose : MonoBehaviour
{
    void Start()
    {
        ApplyHomePose();
    }

    void ApplyHomePose()
    {
        // --- Torso and base adjustments ---
        SetJoint("torso_lift_link", 0f);   // lower torso slightly (was too tall)
        
        // --- Arm joints (inward/folded) ---
        SetJoint("arm_1_link", -20f);        // yaw inward toward body
        SetJoint("arm_2_link", 200f);        // pitch forward/down
        SetJoint("arm_3_link", -70f);        // elbow bends inward
        SetJoint("arm_4_link", -200f);       // wrist moves inward
        SetJoint("arm_5_link", 90f);         // rotate wrist inward
        SetJoint("arm_6_link", -80f);        // fine wrist twist
        SetJoint("arm_7_link", 0f);          // keep neutral

        // --- Optional head orientation ---
        SetJoint("head_1_link", 0f);
        SetJoint("head_2_link", 0f);

        Debug.Log("Tiago set to refined inward 'home' pose.");
    }

    void SetJoint(string name, float angleDeg)
    {
        Transform joint = transform.Find(name);
        if (joint == null)
        {
            Debug.LogWarning($"Joint {name} not found.");
            return;
        }

        // Most Tiago URDFs rotate along local X — invert if rotation direction is wrong
        joint.localRotation = Quaternion.Euler(-angleDeg, 0, 0);
        Debug.Log($"Set {name} → {-angleDeg:F1}°");
    }
}
