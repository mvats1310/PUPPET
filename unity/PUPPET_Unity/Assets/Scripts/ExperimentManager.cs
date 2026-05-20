using UnityEngine;

public class ExperimentManager : MonoBehaviour
{
    public enum Mode { Live, Replay }
    public Mode currentMode = Mode.Live;

    [Header("Tracking")]
    public Transform robot;

    private float startTime;
    private float duration;
    private float pathLength = 0f;

    private Vector3 lastPosition;
    private bool experimentRunning = false;

    void Start()
    {
        if (robot != null)
        {
            lastPosition = robot.position;
        }
    }

    void Update()
    {
        if (!experimentRunning || robot == null) return;

        // Track movement
        float dist = Vector3.Distance(robot.position, lastPosition);
        pathLength += dist;
        lastPosition = robot.position;

        // Track time
        duration = Time.time - startTime;
    }

    // 🔵 Called when experiment starts
    public void StartExperiment()
    {
        Debug.Log("Experiment Started");

        startTime = Time.time;
        pathLength = 0f;

        if (robot != null)
            lastPosition = robot.position;

        experimentRunning = true;
    }

    // 🔴 Called when experiment ends
    public void EndExperiment()
    {
        experimentRunning = false;

        Debug.Log("Experiment Ended");
        Debug.Log("Duration: " + duration);
        Debug.Log("Path Length: " + pathLength);
    }
}