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
                // trigger: up, squeeze: down
                var torso = triggering ? 1 : -1;

                Debug.Log($"torso: {torso}");
                ros.Publish(topicName, new Int32Msg(torso));

                timeElapsed = 0;
            }
        }
    }
}
