using TND.Upscaling.Framework;
using UnityEditor;

namespace TND.Markers
{
    [CustomEditor(typeof(MarkerManager))]
    [CanEditMultipleObjects]
    public class MarkerManagerEditor : Editor
    {
        public override void OnInspectorGUI()
        {
            EditorVisuals.GenerateHeader();

            DrawDefaultInspector();

            EditorVisuals.GenerateFooter();
        }
    }
}
