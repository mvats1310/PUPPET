using UnityEngine;
using UnityEngine.InputSystem;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.BuiltinInterfaces;
using RosMessageTypes.Geometry;
using RosMessageTypes.Std;

public class HeadCommander : MonoBehaviour
{
    private ROSConnection ros;

    public InputActionReference cameraReference = null;
    public InputActionReference enableHeadReference = null;

    public string topicName = "/head_tp_controller/command";

    private bool motionEnabled = false;
    private bool initialOrientationSet = false;

    private Quaternion initialOrientation;
    private Quaternion currentOrientation;

    private Material skybox = null;
    private Color defaultColor;
    private uint seq = 0;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        var topicState = ros.RegisterPublisher<QuaternionStampedMsg>(topicName, 1);
        //topicState.SetMessagePool(new MessagePool<QuaternionStampedMsg>(1000));

        skybox = RenderSettings.skybox;
        defaultColor = Camera.main.backgroundColor;
    }

    private void Awake()
    {
        enableHeadReference.action.performed += OnEnableMotion;
        cameraReference.action.performed += OnChangeOrientation;
    }

    private void OnApplicationQuit()
    {
        enableHeadReference.action.performed -= OnEnableMotion;
        cameraReference.action.performed -= OnChangeOrientation;
    }

    void OnEnableMotion(InputAction.CallbackContext context)
    {
        if (motionEnabled)
        {
            // disable motion and reset initial orientation
            initialOrientationSet = false;

            RenderSettings.skybox = skybox;
            Camera.main.backgroundColor = defaultColor;
        }
        else
        {
            RenderSettings.skybox = null;
            Camera.main.backgroundColor = Color.black;
        }

        motionEnabled = !motionEnabled;
    }

    void OnChangeOrientation(InputAction.CallbackContext context)
    {
        if (motionEnabled)
        {
            if (!initialOrientationSet)
            {
                // get R_A_0
                initialOrientation = Quaternion.Inverse(context.ReadValue<Quaternion>());
                initialOrientationSet = true;
            }
            else
            {
                // R_A_B = R_A_0 * R_0_B
                currentOrientation = initialOrientation * context.ReadValue<Quaternion>();
            }
        }
    }

    void Update()
    {
        if (motionEnabled)
        {
            var now = Time.realtimeSinceStartupAsDouble;

            HeaderMsg header = new(seq: ++seq,
                                   stamp: new TimeMsg((uint)now, (uint)((now % 1.0) * 1e9)),
                                   frame_id: "");

            QuaternionMsg quaternion = new(x: currentOrientation.x,
                                           y: currentOrientation.y,
                                           z: currentOrientation.z,
                                           w: currentOrientation.w);

            ros.Publish(topicName, new QuaternionStampedMsg(header, quaternion));
            //Debug.Log((int)(Time.realtimeSinceStartupAsDouble * 1000.0));
        }
    }
}
