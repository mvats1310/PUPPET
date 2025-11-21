using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;

public class TiagoJointStateReader : MonoBehaviour
{
    public string topicName = "/joint_states";
    private ROSConnection ros;

    private Dictionary<string, Transform> jointMap = new();
    private Dictionary<string, float> jointAngles = new();
    private Dictionary<string, Quaternion> initialRots = new();
    private Dictionary<string, Vector3> initialPos = new();

    private Dictionary<string, Vector3> unityAxes = new()
    {
        { "arm_1_joint", Vector3.right },     // FIXED
        { "arm_2_joint", Vector3.up },        // FIXED
        { "arm_3_joint", Vector3.up },        // FIXED
        { "arm_4_joint", Vector3.forward },   // FIXED
        { "arm_5_joint", Vector3.up },        // FIXED
        { "arm_6_joint", Vector3.forward },   // FIXED
        { "arm_7_joint", Vector3.up },        // FIXED

        { "head_1_joint", Vector3.up },
        { "head_2_joint", Vector3.right }
    };

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<JointStateMsg>(topicName, JointStateCallback);

        foreach (Transform t in GetComponentsInChildren<Transform>())
        {
            jointMap[t.name] = t;
            initialRots[t.name] = t.localRotation;
            initialPos[t.name] = t.localPosition;
        }
    }

    void JointStateCallback(JointStateMsg msg)
    {
        if (msg == null) return;

        int n = Mathf.Min(msg.name.Length, msg.position.Length);
        for (int i = 0; i < n; i++)
        {
            string name = msg.name[i];
            double pos = msg.position[i];

            if (name == "torso_lift_joint")
            {
                jointAngles[name] = (float)pos; 
            }
            else if (unityAxes.ContainsKey(name))
            {
                jointAngles[name] = (float)(pos * Mathf.Rad2Deg);
            }
        }
    }

    void Update()
    {
        foreach (var kvp in jointAngles)
        {
            string name = kvp.Key;
            float value = kvp.Value;

            if (!jointMap.ContainsKey(name)) continue;

            Transform j = jointMap[name];

            if (name == "torso_lift_joint")
            {
                j.localPosition = initialPos[name] + new Vector3(0, value, 0);
            }
            else
            {
                Vector3 axis = unityAxes[name];
                j.localRotation = initialRots[name] * Quaternion.AngleAxis(value, axis);
            }
        }
    }
}
