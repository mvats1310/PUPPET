using UnityEngine;

public class SimpleGrab : MonoBehaviour
{
    public Transform attachPoint;

    private GameObject candidate;
    private Rigidbody candidateRb;
    private bool holding;

    void OnTriggerEnter(Collider other)
    {
        Debug.Log("ENTER: " + other.name);

        if (!other.CompareTag("Grabbable")) return;

        candidate = other.gameObject;
        candidateRb = other.attachedRigidbody;
    }

    void OnTriggerExit(Collider other)
    {
        if (candidate == other.gameObject && !holding)
        {
            candidate = null;
            candidateRb = null;
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.G))
            Grab();

        if (Input.GetKeyDown(KeyCode.R))
            Release();
    }

    void Grab()
    {
        if (candidate == null) return;

        holding = true;

        if (candidateRb != null)
        {
            candidateRb.velocity = Vector3.zero;
            candidateRb.angularVelocity = Vector3.zero;
            candidateRb.useGravity = false;
            candidateRb.isKinematic = true;
        }

        candidate.transform.SetParent(attachPoint);
        candidate.transform.position = attachPoint.position;
        candidate.transform.rotation = attachPoint.rotation;

        Debug.Log("GRABBED");
    }

    void Release()
    {
        if (candidate == null) return;

        candidate.transform.SetParent(null);

        if (candidateRb != null)
        {
            candidateRb.isKinematic = false;
            candidateRb.useGravity = true;
        }

        Debug.Log("RELEASED");

        candidate = null;
        candidateRb = null;
        holding = false;
    }
}