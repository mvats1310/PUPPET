using System;
using System.Reflection;
using UnityEngine;

public class DisablePhysicsForRobot : MonoBehaviour
{
    public enum Mode { GlobalPause, DisableComponents, DestroyComponents }
    public Mode mode = Mode.DisableComponents;

    [Tooltip("If GlobalPause: disable physics simulation for entire scene.")]
    public bool disableGravityAlso = true;

    void Start()
    {
        Apply(mode);
    }

    [ContextMenu("Apply Disable")]
    public void Apply() => Apply(mode);

    void Apply(Mode m)
    {
        if (m == Mode.GlobalPause)
        {
            Physics.autoSimulation = false;
            if (disableGravityAlso) Physics.gravity = Vector3.zero;
            Debug.Log("[DisablePhysicsForRobot] Physics.autoSimulation = false");
            return;
        }

        // operate on this GameObject and children
        var colliders = GetComponentsInChildren<Collider>(true);
        var rbs = GetComponentsInChildren<Rigidbody>(true);
        var abs = GetComponentsInChildren<UnityEngine.ArticulationBody>(true);

        if (m == Mode.DestroyComponents)
        {
            foreach (var c in colliders) DestroyImmediate(c);
            foreach (var rb in rbs) DestroyImmediate(rb);
            foreach (var ab in abs) DestroyImmediate(ab);
            Debug.Log("[DisablePhysicsForRobot] Destroyed colliders/rb/articulationbodies");
            return;
        }

        // Mode.DisableComponents (recommended) - non-destructive
        // 1) KEEP colliders enabled (do NOT disable - otherwise object will pass through floor)
        //    Optionally you can change layers or set specific ignores instead of disabling colliders.
        foreach (var c in colliders)
        {
            try
            {
                // ensure collider remains enabled so physics collisions still block movement
                c.enabled = true;
            }
            catch { }
        }

        // 2) Make Rigidbodies kinematic + no gravity + zero velocities (prevents physics forces)
        foreach (var rb in rbs)
        {
            try
            {
                rb.isKinematic = true;    // use MovePosition/MoveRotation if you move this transform
                rb.useGravity = false;
                rb.velocity = Vector3.zero;
                rb.angularVelocity = Vector3.zero;
            }
            catch { }
        }

        // 3) Handle ArticulationBody safely via reflection (immovable/useGravity/jointFriction may not exist in all Unity versions)
        foreach (var ab in abs)
        {
            var t = ab.GetType();
            // do NOT disable its collider — only turn off gravity / make immovable so it doesn't fall
            TrySetMember(ab, "useGravity", false);
            TrySetMember(ab, "immovable", true);
            // heavy damping as fallback so joint physics don't produce drift
            TrySetMember(ab, "jointFriction", 1e6f);
            TrySetMember(ab, "linearDamping", 1e6f);
            TrySetMember(ab, "angularDamping", 1e6f);

            // If ArticulationBody has xDrive on child joints, set force limits / stiffness/damping to 0 via reflection if needed.
            var xDriveProp = t.GetProperty("xDrive", BindingFlags.Public | BindingFlags.Instance);
            if (xDriveProp != null)
            {
                try
                {
                    object drive = xDriveProp.GetValue(ab);
                    if (drive != null)
                    {
                        var driveType = drive.GetType();
                        TrySetOnObject(drive, "forceLimit", 0f);
                        TrySetOnObject(drive, "stiffness", 0f);
                        TrySetOnObject(drive, "damping", 0f);
                        // write back if it's a struct (boxed)
                        xDriveProp.SetValue(ab, drive);
                    }
                }
                catch { }
            }
        }

        Debug.Log($"[DisablePhysicsForRobot] Disabled physics on {gameObject.name}: colliders disabled={colliders.Length}, rigidbodies kinematic={rbs.Length}, articulation bodies processed={abs.Length}");
    }

    static bool TrySetMember(object target, string name, object value)
    {
        if (target == null) return false;
        var t = target.GetType();
        BindingFlags flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;

        var prop = t.GetProperty(name, flags);
        if (prop != null && prop.CanWrite)
        {
            try { prop.SetValue(target, ConvertToType(value, prop.PropertyType)); return true; } catch { }
        }

        var field = t.GetField(name, flags);
        if (field != null)
        {
            try { field.SetValue(target, ConvertToType(value, field.FieldType)); return true; } catch { }
        }

        return false;
    }

    static bool TrySetOnObject(object obj, string memberName, object value)
    {
        if (obj == null) return false;
        var t = obj.GetType();
        var p = t.GetProperty(memberName, BindingFlags.Public | BindingFlags.Instance);
        if (p != null && p.CanWrite)
        {
            try { p.SetValue(obj, ConvertToType(value, p.PropertyType)); return true; } catch { }
        }
        var f = t.GetField(memberName, BindingFlags.Public | BindingFlags.Instance);
        if (f != null)
        {
            try { f.SetValue(obj, ConvertToType(value, f.FieldType)); return true; } catch { }
        }
        return false;
    }

    static object ConvertToType(object value, Type targetType)
    {
        if (value == null) return null;
        if (targetType.IsInstanceOfType(value)) return value;
        try
        {
            if (targetType.IsEnum && value is string s) return Enum.Parse(targetType, s);
            if (targetType == typeof(Vector3) && value is Vector3) return value;
            return System.Convert.ChangeType(value, targetType);
        }
        catch { return value; }
    }
}