using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Stable grasping for ArticulationBody grippers:
/// - Wait until gripper is "closing"
/// - On contact with Grabbable object: make object kinematic + parent to attach point
/// - Ignore collisions between gripper colliders and held object colliders (prevents jitter)
/// - Release when gripper opens: restore RB + collisions
/// </summary>
public class ArticulationGraspLock : MonoBehaviour
{
    [Header("References")]
    public ArticulationGripperDriver gripperDriver;

    [Tooltip("Where the object will snap to when held.")]
    public Transform attachPoint;

    [Header("Contact Colliders (on the gripper)")]
    [Tooltip("All colliders that can touch the object (finger pads, inner finger links, palm).")]
    public Collider[] gripperColliders;

    [Header("Grabbable Filtering")]
    public string grabbableTag = "Grabbable";

    [Tooltip("If true, only objects with Rigidbody can be grabbed.")]
    public bool requireRigidbody = true;

    [Header("Snap Settings")]
    [Tooltip("If true, snap held object to attach point pose.")]
    public bool snapOnGrab = true;

    [Tooltip("Local position offset applied after snapping.")]
    public Vector3 snapLocalPositionOffset = Vector3.zero;

    [Tooltip("Local rotation offset applied after snapping.")]
    public Vector3 snapLocalEulerOffset = Vector3.zero;

    [Header("Release Settings")]
    [Tooltip("If true, restore gravity on release.")]
    public bool restoreGravity = true;

    [Tooltip("If true, apply a small throw velocity on release (optional).")]
    public bool applyReleaseVelocity = false;

    [Tooltip("Velocity applied in world space when releasing (optional).")]
    public Vector3 releaseVelocity = Vector3.zero;

    [Header("Debug")]
    public bool debugLogs = false;

    Rigidbody heldRigidbody;
    Transform heldTransform;
    bool isHolding;

    // Cache original RB settings to restore cleanly
    bool heldWasKinematic;
    bool heldUsedGravity;
    RigidbodyInterpolation heldInterpolation;
    CollisionDetectionMode heldCollisionMode;

    // Collision ignore bookkeeping
    readonly List<Collider> heldColliders = new();
    readonly List<(Collider a, Collider b)> ignoredPairs = new();

    void Reset()
    {
        // Auto-guess attach point
        attachPoint = transform;
    }

    void Update()
    {
        if (!gripperDriver || !attachPoint) return;

        // Release when gripper opens
        if (isHolding && !gripperDriver.gripperClosed)
        {
            Release();
        }
    }

    void OnCollisionEnter(Collision collision)
    {
        TryGrabFromCollision(collision);
    }

    void OnCollisionStay(Collision collision)
    {
        // Useful if the first contact happens slightly before you "close"
        TryGrabFromCollision(collision);
    }

    void TryGrabFromCollision(Collision collision)
    {
        if (!gripperDriver || !attachPoint) return;

        // Only grab when closing
        if (!gripperDriver.gripperClosed) return;

        if (isHolding) return;

        var other = collision.collider;
        if (!other) return;

        // Filter by tag
        if (!string.IsNullOrEmpty(grabbableTag) && !other.CompareTag(grabbableTag))
            return;

        // Must have rigidbody?
        var rb = other.attachedRigidbody;
        if (requireRigidbody && rb == null) return;

        // If object is part of a larger hierarchy, grab the rigidbody root transform
        if (rb != null)
        {
            Grab(rb);
        }
        else
        {
            // Fallback: grab the collider's transform (not recommended)
            GrabTransformOnly(other.transform);
        }
    }

    void Grab(Rigidbody rb)
    {
        heldRigidbody = rb;
        heldTransform = rb.transform;

        // Cache original RB settings
        heldWasKinematic = rb.isKinematic;
        heldUsedGravity = rb.useGravity;
        heldInterpolation = rb.interpolation;
        heldCollisionMode = rb.collisionDetectionMode;

        // Make stable for parenting
        rb.isKinematic = true;
        rb.useGravity = false;
        rb.velocity = Vector3.zero;
        rb.angularVelocity = Vector3.zero;
        rb.interpolation = RigidbodyInterpolation.None;
        rb.collisionDetectionMode = CollisionDetectionMode.Discrete;

        // Collect held colliders for collision ignoring
        heldColliders.Clear();
        heldTransform.GetComponentsInChildren(true, heldColliders);

        // Parent to attach point
        heldTransform.SetParent(attachPoint, worldPositionStays: true);

        if (snapOnGrab)
        {
            heldTransform.localPosition = snapLocalPositionOffset;
            heldTransform.localRotation = Quaternion.Euler(snapLocalEulerOffset);
        }

        IgnoreGripperObjectCollisions(true);

        isHolding = true;

        if (debugLogs) Debug.Log($"[ArticulationGraspLock] Grabbed: {heldTransform.name}");
    }

    void GrabTransformOnly(Transform t)
    {
        heldTransform = t;
        heldRigidbody = null;

        heldTransform.SetParent(attachPoint, worldPositionStays: true);

        if (snapOnGrab)
        {
            heldTransform.localPosition = snapLocalPositionOffset;
            heldTransform.localRotation = Quaternion.Euler(snapLocalEulerOffset);
        }

        isHolding = true;

        if (debugLogs) Debug.Log($"[ArticulationGraspLock] Grabbed (no RB): {heldTransform.name}");
    }

    void Release()
    {
        if (!isHolding) return;

        if (debugLogs) Debug.Log($"[ArticulationGraspLock] Releasing: {heldTransform?.name}");

        IgnoreGripperObjectCollisions(false);

        if (heldTransform)
            heldTransform.SetParent(null, worldPositionStays: true);

        if (heldRigidbody)
        {
            // Restore RB settings
            heldRigidbody.isKinematic = heldWasKinematic;
            heldRigidbody.useGravity = restoreGravity ? heldUsedGravity : false;
            heldRigidbody.interpolation = heldInterpolation;
            heldRigidbody.collisionDetectionMode = heldCollisionMode;

            if (applyReleaseVelocity)
            {
                heldRigidbody.velocity = releaseVelocity;
            }
        }

        heldColliders.Clear();
        ignoredPairs.Clear();

        heldRigidbody = null;
        heldTransform = null;
        isHolding = false;
    }

    void IgnoreGripperObjectCollisions(bool ignore)
    {
        if (gripperColliders == null || gripperColliders.Length == 0) return;
        if (heldColliders == null || heldColliders.Count == 0) return;

        if (ignore)
        {
            ignoredPairs.Clear();

            foreach (var gCol in gripperColliders)
            {
                if (!gCol) continue;

                foreach (var oCol in heldColliders)
                {
                    if (!oCol) continue;

                    // Record & ignore
                    Physics.IgnoreCollision(gCol, oCol, true);
                    ignoredPairs.Add((gCol, oCol));
                }
            }
        }
        else
        {
            // Restore only what we ignored
            foreach (var pair in ignoredPairs)
            {
                if (pair.a && pair.b)
                    Physics.IgnoreCollision(pair.a, pair.b, false);
            }
        }
    }

    // Optional: call this externally if you need a forced drop (teleport / reset)
    public void ForceRelease()
    {
        if (isHolding) Release();
    }
}
