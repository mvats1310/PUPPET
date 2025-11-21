using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

public class InputTest : MonoBehaviour
{
    public InputActionReference leftButtonX;
    public InputActionReference leftButtonY;
    public InputActionReference leftTrigger;
    public InputActionReference leftGrip;

    public InputActionReference rightButtonA;
    public InputActionReference rightButtonB;
    public InputActionReference rightTrigger;
    public InputActionReference rightGrip;

    void Start()
    {
        Debug.Log("starting");

        leftButtonX.action.performed += context => Debug.Log("leftButtonX performed");
        leftButtonX.action.canceled += context => Debug.Log("leftButtonX canceled");

        leftButtonY.action.performed += context => Debug.Log("leftButtonY performed");
        leftButtonY.action.canceled += context => Debug.Log("leftButtonY canceled");

        leftTrigger.action.performed += context => Debug.Log("leftTrigger performed");
        leftTrigger.action.canceled += context => Debug.Log("leftTrigger canceled");

        leftGrip.action.performed += context => Debug.Log("leftGrip performed");
        leftGrip.action.canceled += context => Debug.Log("leftGrip canceled");

        rightButtonA.action.performed += context => Debug.Log("rightButtonA performed");
        rightButtonA.action.canceled += context => Debug.Log("rightButtonA canceled");

        rightButtonB.action.performed += context => Debug.Log("rightButtonB performed");
        rightButtonB.action.canceled += context => Debug.Log("rightButtonB canceled");

        rightTrigger.action.performed += context => Debug.Log("rightTrigger performed");
        rightTrigger.action.canceled += context => Debug.Log("rightTrigger canceled");

        rightGrip.action.performed += context => Debug.Log("rightGrip performed");
        rightGrip.action.canceled += context => Debug.Log("rightGrip canceled");
    }

    void Update()
    { }
}
