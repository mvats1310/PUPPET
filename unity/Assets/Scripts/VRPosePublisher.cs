using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;

public class VRPosePublisher : MonoBehaviour
{
    public Transform controller;
    public string topicName = "/vr_pose";
    public float publishRate = 0.02f; // 50 Hz
    ROSConnection ros;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(topicName);
        InvokeRepeating(nameof(PublishPose), 1.0f, publishRate);
    }

    void PublishPose()
    {
        if (controller == null) return;
        var pos = controller.position;
        var rot = controller.rotation;
        var poseMsg = new PoseStampedMsg
        {
            pose = new PoseMsg(
                new PointMsg(pos.x, pos.y, pos.z),
                new QuaternionMsg(rot.x, rot.y, rot.z, rot.w)
            )
        };
        ros.Publish(topicName, poseMsg);
    }
}
