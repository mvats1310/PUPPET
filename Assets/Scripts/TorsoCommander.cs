using UnityEngine;
using UnityEngine.InputSystem;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;

public class TorsoCommander : MonoBehaviour
{
    private ROSConnection ros;

    public InputActionReference triggerReference = null;
    public InputActionReference squeezeReference = null;

    public string topicName = "/torso_tp_controller/command";
    public float publishMessageFrequency = 0.02f; // [s]

    private bool triggering;
    private bool squeezing;
    private float triggerValue;
    private float squeezeValue;
    private float timeElapsed;

    private void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<Int32Msg>(topicName);
    }

    private void Awake()
    {
        triggerReference.action.performed += context => triggering = true;
        triggerReference.action.canceled += context => triggering = false;

        squeezeReference.action.performed += context => squeezing = true;
        squeezeReference.action.canceled += context => squeezing = false;
    }

    void Update()
    {
        if (triggering ^ squeezing)
        {
            timeElapsed += Time.deltaTime;

            if (timeElapsed > publishMessageFrequency)
            {
                // compute desiredHeight (replace this with your actual calculation)
                float desiredHeight = triggering ? 0.35f : 0.0f;

                // clamp to valid range
                float clamped = Mathf.Clamp(desiredHeight, 0.0f, 0.35f);
                desiredHeight = clamped;

                // publish clamped value (use the correct message type for your topic)
                ros.Publish(topicName, new RosMessageTypes.Std.Float32Msg(desiredHeight));

                timeElapsed = 0;
            }
        }
    }
}
