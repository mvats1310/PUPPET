using System.Collections.Generic;
using UnityEngine;

namespace TND.Markers
{
    [System.Serializable]
    public class MarkerType
    {
        [Header("Marker Settings")]
        public string TypeName = "Default Marker";

        [Header("Toggle Settings")]
        [Tooltip("The text that will be displayed on the marker.")]
        public bool DisplayName = true;
        [Tooltip("The distance, from player to marker, that will be displayed on the marker.")]
        public bool DisplayDistance = true;
        [Tooltip("Toggle displaying an off-screen arrow visual.")]
        public bool DisplayOffscreenArrow = true;
        [Tooltip("Toggle displaying the marker name when off-screen.")]
        public bool OffscreenNameFadeout = true;
        [Tooltip("Toggle displaying the distance when off-screen.")]
        public bool OffscreenDistanceFadeout = true;

        [Header("Visual Settings")]
        [Tooltip("The 2D marker visual.")]
        public Texture2D Visual;
        [Tooltip("The 2D marker off-screen arrow visual.")]
        public Texture2D OffscreenArrowVisual;

        [Header("Distance Settings")]
        [Tooltip("The minimum distance for the marker to show.")]
        public float MinimumDistance = 0;
        [Tooltip("The maximum distance for the marker to show.")]
        public float MaximumDistance = Mathf.Infinity;

        [Header("Suffix Settings")]
        [Tooltip("A helpful extra appendix added to the distance text.")]
        public string DistanceSuffix = "m";
    }

    [CreateAssetMenu(fileName = "MarkerSettings", menuName = "TND/Markers/Settings", order = 1)]
    public class MarkerSettings : SingletonScriptableObjectEditor<MarkerSettings>
    {
        [Header("References:")]
        [Tooltip("Prefab of Marker.")]
        public MarkerController MarkerTemplatePrefab;

        [Tooltip("Types of Markers.")]
        public List<MarkerType> MarkerTypes = new List<MarkerType>();

        // Make sure no duplicate MarkerTypes can exist.
        public void OnValidate()
        {
            HashSet<string> existingNames = new HashSet<string>();
            for (int i = 0; i < MarkerTypes.Count; i++)
            {
                string currentName = MarkerTypes[i].TypeName;

                if (existingNames.Contains(currentName))
                {
                    Debug.LogError($"[Markers] Duplicate _thisMarkerController TypeName detected: \"{currentName}\" at index {i} in MarkerTypes list.", this);
                }
                else
                {
                    existingNames.Add(currentName);
                }
            }

            MarkerComponent[] markers = FindObjectsByType<MarkerComponent>(FindObjectsSortMode.None);
            for (int i = 0; i < markers.Length; i++)
            {
                markers[i].ValidateMarkerType();
            }
        }
    }
}
