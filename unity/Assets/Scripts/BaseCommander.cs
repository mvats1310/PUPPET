using UnityEngine;
using UnityEngine.InputSystem;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;

public class BaseCommander : MonoBehaviour
{
    private ROSConnection ros;

    public InputActionReference leftScrollReference = null;
    public InputActionReference rightScrollReference = null;

    public string topicName = "/mobile_base_controller/cmd_vel";
    public float publishMessageFrequency = 0.02f; // [s]

    private bool scrollingLeft;
    private bool scrollingRight;
    private Vector2 leftScrollValue;
    private Vector2 rightScrollValue;
    private float timeElapsed;

    private void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<TwistMsg>(topicName);
    }

    private void Awake()
    {
        leftScrollReference.action.started += context => scrollingLeft = true;
        leftScrollReference.action.performed += context => leftScrollValue = context.ReadValue<Vector2>();
        leftScrollReference.action.canceled += context => scrollingLeft = false;

        rightScrollReference.action.started += context => scrollingRight = true;
        rightScrollReference.action.performed += context => rightScrollValue = context.ReadValue<Vector2>();
        rightScrollReference.action.canceled += context => scrollingRight = false;
    }

    private void Update()
    {
        if (!scrollingLeft && !scrollingRight)
        {
            return;
        }

        timeElapsed += Time.deltaTime;

        if (timeElapsed > publishMessageFrequency)
        {
            var left = scrollingLeft ? leftScrollValue.y : .0f;
            var right = scrollingRight ? rightScrollValue.x : .0f;

            Debug.Log($"left: {left}, right: {right}");

            // x: right, y: up
            TwistMsg twist = new(
                linear: new(x: left, y: 0, z: 0),
                angular: new(x: 0, y: 0, z: -right)
            );

            ros.Publish(topicName, twist);

            timeElapsed = 0;
        }
    }
}
