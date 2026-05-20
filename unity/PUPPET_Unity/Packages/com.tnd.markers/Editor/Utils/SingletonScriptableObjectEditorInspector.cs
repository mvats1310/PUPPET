using UnityEditor;

namespace TND.Markers
{
    [CustomEditor(typeof(SingletonScriptableObjectEditor<>), true, isFallback = false)]
    public class SingletonScriptableObjectEditorInspector : Editor
    {

        private bool _assetInResourcesFolder = true;

        public void OnEnable()
        {
            _assetInResourcesFolder = false;
            string assetPath = AssetDatabase.GetAssetPath(target);
            string[] assetPathDirectories = assetPath.Split('/');
            foreach (string pathSegment in assetPathDirectories)
            {
                if (pathSegment == "Resources")
                {
                    _assetInResourcesFolder = true;
                    break;
                }
            }
        }

        public override void OnInspectorGUI()
        {
            if (!_assetInResourcesFolder)
            {
                EditorGUILayout.HelpBox("Error, SingletonScriptableObjectEditor assets need to be placed in a Resource (sub-)folder!", MessageType.Error);
            }

            base.OnInspectorGUI();
        }
    }
}
