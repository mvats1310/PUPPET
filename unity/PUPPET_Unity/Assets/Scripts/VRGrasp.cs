using UnityEngine;

public class VRGrasp : MonoBehaviour
{
    private GameObject heldObject;

    void OnTriggerEnter(Collider other)
    {
        if (heldObject != null) return;
        if (!other.CompareTag("Grabbable")) return;

        heldObject = other.gameObject;

        Rigidbody rb = heldObject.GetComponent<Rigidbody>();
        rb.isKinematic = true;
        rb.useGravity = false;

        heldObject.transform.SetParent(transform);
        heldObject.transform.localPosition = Vector3.zero;
        heldObject.transform.localRotation = Quaternion.identity;
    }

    public void Release()
    {
        if (heldObject == null) return;

        Rigidbody rb = heldObject.GetComponent<Rigidbody>();

        heldObject.transform.SetParent(null);
        rb.isKinematic = false;
        rb.useGravity = true;

        heldObject = null;
    }
}
