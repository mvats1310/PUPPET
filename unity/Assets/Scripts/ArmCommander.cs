using UnityEngine;
using UnityEngine.InputSystem;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.BuiltinInterfaces;
using RosMessageTypes.Geometry;
using RosMessageTypes.TiagoTelepresenceControllers;
using RosMessageTypes.Std;

public class ArmCommander : MonoBehaviour
{
    private ROSConnection ros;

    public InputActionReference armPositionReference = null;
    public InputActionReference armOrientationReference = null;
    public InputActionReference extendArmReference = null;
    public InputActionReference enableArmReference = null;

    public string topicName = "/arm_tp_controller/command";
    public string serviceName = "/tp_arm_motion/command";

    private bool motionEnabled = false;
    private bool armExtended = false;
    private bool processingServiceRequest = false;

    private bool initialPositionSet = false;
    private bool initialOrientationSet = false;

    private Vector3 initialPosition;
    private Vector3 currentPosition;

    private Quaternion initialOrientation;
    private Quaternion currentOrientation;

    private float awaitingResponseUntilTimeout = -1;
    private uint seq = 0;

    private const string HOME_MOTION = "home";
    private const string EXTEND_MOTION = "offer";

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(topicName, 1);
        ros.RegisterRosService<ArmMotionRequest, ArmMotionResponse>(serviceName);
    }

    private void Awake()
    {
        enableArmReference.action.performed += OnEnableMotion;
        extendArmReference.action.performed += OnExtendArm;
        armPositionReference.action.performed += OnChangePosition;
        armOrientationReference.action.performed += OnChangeOrientation;
    }

    private void OnApplicationQuit()
    {
        enableArmReference.action.performed -= OnEnableMotion;
        extendArmReference.action.performed -= OnExtendArm;
        armPositionReference.action.performed -= OnChangePosition;
        armOrientationReference.action.performed -= OnChangeOrientation;
    }

    void OnEnableMotion(InputAction.CallbackContext context)
    {
        if (motionEnabled)
        {
            awaitingResponseUntilTimeout = -1;
            processingServiceRequest = false;
        }
        else
        {
            initialPositionSet = initialOrientationSet = false;
        }

        motionEnabled = !motionEnabled;
    }

    void OnExtendArm(InputAction.CallbackContext context)
    {
        if (motionEnabled && !processingServiceRequest)
        {
            var motion = armExtended ? HOME_MOTION : EXTEND_MOTION;
            Debug.Log($"Sending motion request: {motion}");
            var request = new ArmMotionRequest(motion);
            ros.SendServiceMessage<ArmMotionResponse>(serviceName, request, OnArmMotionResponse);
            awaitingResponseUntilTimeout = Time.time + (armExtended ? 15.0f : 10.0f);
            processingServiceRequest = true;
        }
    }

    void OnChangePosition(InputAction.CallbackContext context)
    {
        if (motionEnabled && armExtended)
        {
            if (!initialPositionSet)
            {
                currentPosition = initialPosition = context.ReadValue<Vector3>();
                initialPositionSet = true;
            }
            else
            {
                currentPosition = context.ReadValue<Vector3>() - initialPosition;
            }
        }
    }

    void OnChangeOrientation(InputAction.CallbackContext context)
    {
        if (motionEnabled && armExtended)
        {
            if (!initialOrientationSet)
            {
                // get R_A_0
                currentOrientation = initialOrientation = Quaternion.Inverse(context.ReadValue<Quaternion>());
                initialOrientationSet = true;
            }
            else
            {
                // R_A_B = R_A_0 * R_0_B
                currentOrientation = initialOrientation * context.ReadValue<Quaternion>();
            }
        }
    }

    void OnArmMotionResponse(ArmMotionResponse response)
    {
        if (response.success)
        {
            initialPositionSet = initialOrientationSet = false;
            armExtended = !armExtended;
            Debug.Log("Arm motion ended");
        }
        else
        {

           Debug.LogError($"Arm motion failed: {response.message}");
        }

        awaitingResponseUntilTimeout = -1;
        processingServiceRequest = false;
    }

    void Update()
    {
        if (motionEnabled)
        {
            if (processingServiceRequest)
            {
                if (Time.time > awaitingResponseUntilTimeout)
                {
                    Debug.Log("Motion timed out!");
                    awaitingResponseUntilTimeout = -1;
                    processingServiceRequest = false;
                }
            }
            else if (armExtended && initialPositionSet && initialOrientationSet)
            {
                // the following code accounts for the transformation between Unity's camera frame (levorotatory)
                // and TIAGo's gripper grasping frame (dextrorotatory) while the arm is extended

                var now = Time.realtimeSinceStartupAsDouble;

                HeaderMsg header = new(seq: ++seq,
                                       stamp: new TimeMsg((uint)now, (uint)((now % 1.0) * 1e9)),
                                       frame_id: "");

                PointMsg position = new(x: currentPosition.z, //forward backward swap
                                        y: currentPosition.x, //left right swap
                                        z: -currentPosition.y); //up down swap

                QuaternionMsg orientation = new(x: currentOrientation.z,
                                                y: currentOrientation.x,
                                                z: currentOrientation.y, 
                                                w: currentOrientation.w); 

                ros.Publish(topicName, new PoseStampedMsg(header, new PoseMsg(position, orientation)));
            }
        }
    }
}