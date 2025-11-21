using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Nav;

public class TiagoOdomSubscriber : MonoBehaviour
{
    public string odomTopic = "/mobile_base_controller/odom";
    public float positionLerpSpeed = 2f;
    public float rotationLerpSpeed = 5f;

    private ROSConnection ros;
    private Vector3 targetPos;
    private Quaternion targetRot;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<OdometryMsg>(odomTopic, UpdatePose);
    }

    void UpdatePose(OdometryMsg msg)
    {
        // Convert ROS (X,Y,Z) → Unity (X,Z,Y)
        targetPos = new Vector3(
            (float)msg.pose.pose.position.x,
            (float)msg.pose.pose.position.z,
            (float)msg.pose.pose.position.y
        );

        var q = msg.pose.pose.orientation;
        targetRot = new Quaternion(
            (float)q.x,
            (float)q.z,
            (float)q.y,
            -(float)q.w
        );
    }

    void Update()
    {
        transform.localPosition = Vector3.Lerp(transform.localPosition, targetPos, Time.deltaTime * positionLerpSpeed);
        transform.localRotation = Quaternion.Slerp(transform.localRotation, targetRot, Time.deltaTime * rotationLerpSpeed);
    }
}
