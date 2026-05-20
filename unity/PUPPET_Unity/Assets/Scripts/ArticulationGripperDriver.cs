using UnityEngine;

public class ArticulationGripperDriver : MonoBehaviour
{
    [Header("Finger Joint Articulations")]
    public UnityEngine.ArticulationBody[] fingerJoints;

    [Header("Drive Parameters")]
    public float stiffness = 150f;
    public float damping = 60f;
    public float forceLimit = 120f;

    [Header("Targets")]
    public float openTarget = 0f;
    public float closedTarget = 25f;

    public bool gripperClosed = false;

    float currentTarget;

    void Start()
    {
        currentTarget = openTarget;
        ConfigureDrives();
        ApplyTarget(openTarget);
    }

    void FixedUpdate()
    {
        float desired = gripperClosed ? closedTarget : openTarget;

        if (!Mathf.Approximately(currentTarget, desired))
        {
            currentTarget = Mathf.Lerp(currentTarget, desired, Time.fixedDeltaTime * 12f);
            ApplyTarget(currentTarget);
        }
    }

    void ConfigureDrives()
    {
        foreach (var joint in fingerJoints)
        {
            if (!joint) continue;

            var drive = joint.xDrive;
            drive.stiffness = stiffness;
            drive.damping = damping;
            drive.forceLimit = forceLimit;
            joint.xDrive = drive;
        }
    }

    void ApplyTarget(float target)
    {
        foreach (var joint in fingerJoints)
        {
            if (!joint) continue;

            var drive = joint.xDrive;
            drive.target = target;
            joint.xDrive = drive;
        }
    }
}
