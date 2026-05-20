using UnityEngine;

public class ModeManager : MonoBehaviour
{
    public GameObject vrTeleopInput;

    public ArmCommander armCommander;
    public BaseCommander baseCommander;
    public GripperGrabber gripperGrabber;

    private bool isEmbodied = false;

    void Start()
    {
        ActivateVisitorMode();
    }

    public void ActivateVisitorMode()
    {
        vrTeleopInput.SetActive(false);

        armCommander.enabled = false;
        baseCommander.enabled = false;
        gripperGrabber.enabled = false;

        isEmbodied = false;
        Debug.Log("Visitor Mode");
    }

    public void ActivateTiagoMode()
    {
        vrTeleopInput.SetActive(true);

        armCommander.enabled = true;
        baseCommander.enabled = true;
        gripperGrabber.enabled = true;

        isEmbodied = true;
        Debug.Log("TIAGo Mode");
    }
}
