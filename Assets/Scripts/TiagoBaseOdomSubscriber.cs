using System.Reflection;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Nav;

public class TiagoBaseOdomSubscriber : MonoBehaviour
{
    public string topicName = "/mobile_base_controller/odom";
    private ROSConnection ros;

    // Optional debug counter
    private int msgCount = 0;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<OdometryMsg>(topicName, UpdateBasePose);
        Debug.Log($"[TiagoBaseOdomSubscriber] Subscribed to {topicName}");

        // Disable physics influence if present
        if (TryGetComponent(out Rigidbody rb))
        {
            rb.isKinematic = true;
            rb.useGravity = false;
        }

        // Reflection-safe handling for ArticulationBody (immovable/useGravity may not be available at compile-time)
        if (TryGetComponent(out ArticulationBody ab))
        {
            var abType = typeof(ArticulationBody);
            // immovable (may be present in some Unity versions / inspector)
            var immovableProp = abType.GetProperty("immovable", BindingFlags.Public | BindingFlags.Instance);
            if (immovableProp != null && immovableProp.PropertyType == typeof(bool))
            {
                try { immovableProp.SetValue(ab, true); }
                catch { }
            }
            else
            {
                // fallback: try setting available friction/damping-like members via reflection
                TrySetMember(ab, "jointFriction", 1e6f);
                TrySetMember(ab, "linearDamping", 1e6f);
                TrySetMember(ab, "angularDamping", 1e6f);
                TrySetMember(ab, "jointFriction", 1e6f);
            }

            // useGravity (may not exist as a member in some Unity versions)
            var useGravityProp = abType.GetProperty("useGravity", BindingFlags.Public | BindingFlags.Instance);
            if (useGravityProp != null && useGravityProp.PropertyType == typeof(bool))
            {
                try { useGravityProp.SetValue(ab, false); }
                catch { }
            }
        }
    }

    void UpdateBasePose(OdometryMsg msg)
    {
        Vector3 rosPos = new Vector3(
            (float)msg.pose.pose.position.y,
            (float)msg.pose.pose.position.z,
            (float)msg.pose.pose.position.x
        );

        Quaternion rosRot = new Quaternion(
            (float)msg.pose.pose.orientation.y,
            (float)msg.pose.pose.orientation.z,
            (float)msg.pose.pose.orientation.x,
            (float)msg.pose.pose.orientation.w
        );

        // Optional debug logging
        msgCount++;
        Debug.Log($"[TiagoBaseOdomSubscriber] msg#{msgCount} ROS pos={rosPos} rot(euler)={rosRot.eulerAngles}");

        // Apply position and rotation
        transform.localPosition = rosPos;
        transform.localRotation = rosRot;
    }

    // Add these helpers at the end of the file (or anywhere inside the same class/file)
    static bool TrySetMember(object target, string name, object value)
    {
        if (target == null) return false;
        var t = target.GetType();
        BindingFlags flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;

        var prop = t.GetProperty(name, flags);
        if (prop != null && prop.CanWrite)
        {
            try
            {
                object v = ConvertToType(value, prop.PropertyType);
                prop.SetValue(target, v);
                return true;
            }
            catch { return false; }
        }

        var field = t.GetField(name, flags);
        if (field != null)
        {
            try
            {
                object v = ConvertToType(value, field.FieldType);
                field.SetValue(target, v);
                return true;
            }
            catch { return false; }
        }

        return false;
    }

    static object ConvertToType(object value, System.Type targetType)
    {
        if (value == null) return null;
        var valType = value.GetType();
        if (targetType.IsAssignableFrom(valType)) return value;
        try
        {
            if (targetType == typeof(Vector3) && value is Vector3) return value;
            return System.Convert.ChangeType(value, targetType);
        }
        catch { return value; }
    }
}
