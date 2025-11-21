using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;
using UnityEngine.InputSystem;

public class HeadSubscriber : MonoBehaviour
{
    private ROSConnection ros;

    public InputActionReference headReference = null;

    public string topicName = "/head_tp_controller/state";

    private Vector3 headOrientation;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<Float32MultiArrayMsg>(topicName, StateCallback);
    }

    void StateCallback(Float32MultiArrayMsg msg)
    {
        headOrientation = new(msg.data[0], msg.data[1], .0f);
    }

    void Update()
    {
        //Debug.Log($"head: {headOrientation}");
    }
}
