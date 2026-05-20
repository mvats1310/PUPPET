using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

public class TiagoVRInput : MonoBehaviour
{
    public ActionBasedController controller;
    public VRGrasp vrGrasp;

    void Update()
    {
        // Release object when grip/activate is released
        if (controller.activateAction.action.WasReleasedThisFrame())
        {
            vrGrasp.Release();   // ✅ THIS IS STEP 4
        }
    }
}
