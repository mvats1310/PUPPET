using System;
using System.Collections.Generic;
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
    public float publishMessageFrequency = 0.02f;

    [Header("Speed Tuning")]
    public float maxLinearSpeed = 0.18f;
    public float linearAccel = 0.35f;
    // make rotation as slow and gentle as linear motion
    public float maxAngularSpeed = 0.18f;
    public float angularAccel = 0.35f;

    private float currentLinear = 0f;
    private float currentAngular = 0f;

    private bool scrollingLeft;
    private bool scrollingRight;
    private Vector2 leftScrollValue;
    private Vector2 rightScrollValue;
    private float timeElapsed;

    [Header("Collision Detection")]
    public bool enableCollisionDetection = true;

    [Header("Base Bumpers")]
    public GameObject frontBumper = null;
    public GameObject rearBumper = null;

    [Header("Arm Bumpers")]
    [Tooltip("Drag all arm bumpers here")]
    public List<GameObject> armBumpers = new List<GameObject>();

    private bool frontColliding = false;
    private bool rearColliding  = false;
    private int  armCollisionCount = 0;
    private bool armHitWhileMovingForward = false;

    private bool AnyArmColliding => armCollisionCount > 0;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<TwistMsg>(topicName);

        if (enableCollisionDetection)
        {
            SetupBumper(frontBumper,
                () => {
                    frontColliding = true;
                    EmergencyStop();
                    Debug.Log("🔴 FRONT hit");
                },
                () => { 
                    frontColliding = false; 
                    Debug.Log("🟢 FRONT clear"); 
                });

            SetupBumper(rearBumper,
                () => {
                    rearColliding = true;
                    EmergencyStop();
                    Debug.Log("🔴 REAR hit");
                },
                () => { 
                    rearColliding = false;  
                    Debug.Log("🟢 REAR clear"); 
                });

            for (int i = 0; i < armBumpers.Count; i++)
            {
                int index = i;
                SetupBumper(armBumpers[i],
                    () => {
                        armCollisionCount++;
                        armHitWhileMovingForward = currentLinear >= 0;
                        EmergencyStop();
                        Debug.Log($"🔴 ARM bumper {index} hit | total: {armCollisionCount}");
                    },
                    () => {
                        armCollisionCount = Mathf.Max(0, armCollisionCount - 1);
                        Debug.Log($"🟢 ARM bumper {index} clear | remaining: {armCollisionCount}");
                    });
            }

            Debug.Log($"✅ Configured: Front + Rear + {armBumpers.Count} arm bumpers");
        }
    }

    private void EmergencyStop()
    {
        currentLinear  = 0f;
        currentAngular = 0f;
        ros.Publish(topicName, new TwistMsg(
            linear:  new Vector3Msg(x: 0, y: 0, z: 0),
            angular: new Vector3Msg(x: 0, y: 0, z: 0)
        ));
        Debug.Log("🛑 EMERGENCY STOP");
    }

    private void SetupBumper(GameObject bumper, Action onEnter, Action onExit)
    {
        if (bumper == null) return;

        Collider col = bumper.GetComponent<Collider>();
        if (col == null)
        {
            Debug.LogError($"{bumper.name} has no Collider!");
            return;
        }

        col.isTrigger = true;

        BumperCollision script = bumper.GetComponent<BumperCollision>();
        if (script == null)
            script = bumper.AddComponent<BumperCollision>();

        script.detectionLayers  = LayerMask.GetMask("Obstacle");
        script.onCollisionEnter = onEnter;
        script.onCollisionExit  = onExit;

        Debug.Log($"✅ {bumper.name} configured");
    }

    private void Awake()
    {
        if (leftScrollReference?.action != null)
        {
            leftScrollReference.action.started   += _ => scrollingLeft = true;
            leftScrollReference.action.performed += ctx => leftScrollValue = ctx.ReadValue<Vector2>();
            leftScrollReference.action.canceled  += _ => scrollingLeft = false;
        }

        if (rightScrollReference?.action != null)
        {
            rightScrollReference.action.started   += _ => scrollingRight = true;
            rightScrollReference.action.performed += ctx => rightScrollValue = ctx.ReadValue<Vector2>();
            rightScrollReference.action.canceled  += _ => scrollingRight = false;
        }
    }

    private void Update()
    {
        if (!scrollingLeft && !scrollingRight)
        {
            currentLinear  = Mathf.MoveTowards(currentLinear,  0f, linearAccel  * Time.deltaTime);
            currentAngular = Mathf.MoveTowards(currentAngular, 0f, angularAccel * Time.deltaTime);
            PublishTwist(currentLinear, currentAngular);
            return;
        }

        timeElapsed += Time.deltaTime;

        if (timeElapsed > publishMessageFrequency)
        {
            float left  = scrollingLeft  ? leftScrollValue.y  : 0f;
            float right = scrollingRight ? rightScrollValue.x : 0f;

            float desiredLinear  = left  *  maxLinearSpeed;
            float desiredAngular = right * -maxAngularSpeed;

            if (enableCollisionDetection)
            {
                // FRONT bumper
                if (frontColliding && desiredLinear > 0)
                {
                    desiredLinear = 0f;
                    desiredAngular = 0f; // stop turning when front is hit
                    Debug.LogWarning("⚠️ FRONT blocked → stop and reverse to escape");
                }

                // REAR bumper
                if (rearColliding && desiredLinear < 0)
                {
                    desiredLinear = 0f;
                    desiredAngular = 0f; // stop turning when rear is hit
                    Debug.LogWarning("⚠️ REAR blocked → stop and forward to escape");
                }

                // ARM bumpers
                if (AnyArmColliding)
                {
                    if (armHitWhileMovingForward && desiredLinear > 0)
                    {
                        desiredLinear = 0f;
                        Debug.LogWarning("⚠️ ARM blocked forward → stop and reverse to escape");
                    }
                    else if (!armHitWhileMovingForward && desiredLinear < 0)
                    {
                        desiredLinear = 0f;
                        Debug.LogWarning("⚠️ ARM blocked backward → stop and forward to escape");
                    }

                    // allow a small angular input that turns AWAY from the obstacle:
                    float armAngularLimit = maxAngularSpeed * 0.25f; // tune this factor in the Inspector
                    bool escapeTurn = (armHitWhileMovingForward && desiredAngular < 0f)
                                   || (!armHitWhileMovingForward && desiredAngular > 0f);

                    if (escapeTurn)
                    {
                        // permit turning but clamp magnitude so you can spin away slowly
                        desiredAngular = Mathf.Clamp(desiredAngular, -armAngularLimit, armAngularLimit);
                    }
                    else
                    {
                        // block turning that would push the arm further into contact
                        desiredAngular = 0f;
                    }
                }
            }

            // Smooth towards clamped desired speeds
            currentLinear  = Mathf.MoveTowards(currentLinear,  desiredLinear,  linearAccel  * Time.deltaTime);
            currentAngular = Mathf.MoveTowards(currentAngular, desiredAngular, angularAccel * Time.deltaTime);

            PublishTwist(currentLinear, currentAngular);
            timeElapsed = 0;
        }
    }

    private void PublishTwist(float linear, float angular)
    {
        ros.Publish(topicName, new TwistMsg(
            linear:  new Vector3Msg(x: linear,  y: 0, z: 0),
            angular: new Vector3Msg(x: 0, y: 0, z: angular)
        ));
    }
}
