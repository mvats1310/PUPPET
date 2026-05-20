using UnityEngine;
using UnityEditor;
using TND.Upscaling.Framework;

namespace TND.Markers
{
    [CustomEditor(typeof(MarkerComponent))]
    [CanEditMultipleObjects]
    public class MarkerComponentEditor : Editor
    {
        private MarkerComponent _component;
        private SerializedProperty _script;

        private int _selectedType;
        private string[] _typeOptions;

        private void OnEnable()
        {
            _component = target as MarkerComponent;

            _script = serializedObject.FindProperty("m_Script");
        }

        public override void OnInspectorGUI()
        {
            EditorVisuals.GenerateHeader();

            _typeOptions = new string[MarkerSettings.Instance.MarkerTypes.Count];
            for (int i = 0; i < MarkerSettings.Instance.MarkerTypes.Count; i++)
            {
                _typeOptions[i] = MarkerSettings.Instance.MarkerTypes[i].TypeName;
            }

            serializedObject.Update();
            EditorGUI.BeginDisabledGroup(true);
            EditorGUILayout.PropertyField(_script);
            EditorGUI.EndDisabledGroup();

            _selectedType = EditorGUILayout.Popup("Marker Type", Mathf.Clamp(_component.MarkerType, 0, MarkerSettings.Instance.MarkerTypes.Count), _typeOptions);
            _component.MarkerType = _selectedType;
            string[] excludedProperties = new string[] { "m_Script", "MarkerType" };
            DrawPropertiesExcluding(serializedObject, excludedProperties);
            serializedObject.ApplyModifiedProperties();

            _component.ValidateMarkerType();

            EditorVisuals.GenerateFooter();
        }


    }
}
