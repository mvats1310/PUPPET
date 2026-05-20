using System.Linq;
using TND.Markers;
using UnityEngine;

/// <summary>
/// Abstract class for making reload-proof singletons out of ScriptableObjects
/// Returns the asset created on the editor, or null if there is none
/// Based on https://www.youtube.com/watch?v=VBA1QCoEAX4
/// </summary>
/// <typeparam name="T">Singleton type</typeparam>
namespace TND.Markers
{
    public abstract class SingletonScriptableObjectEditor<T> : ScriptableObject where T : ScriptableObject
    {
        static T _instance = null;
        public static T Instance
        {
            get
            {
                if (!_instance)
                {
                    // NOTE: Check if there is already an instance of type T loaded.
#if UNITY_2023_1_OR_NEWER
                _instance = FindAnyObjectByType<T>();// GameObject.FindGameObjectWithTag("Player").transform;
#else
                    _instance = FindObjectsOfType<T>().FirstOrDefault();
#endif

                    if (!_instance)
                    {
                        _instance = Resources.FindObjectsOfTypeAll<T>().FirstOrDefault();
                        if (!_instance)
                        {
                            // NOTE: Load the file from disk and return that instance.
                            _instance = Resources.LoadAll<T>("").FirstOrDefault();
                            if (!_instance)
                            {
                                Debug.LogError($"[{nameof(T)}] Could not find an asset in the Resources folder of type {nameof(T)}. Did you forget to create the asset or did you not place the asset into a Resources folder? Creating an empty one..");

                                // NOTE: If there is no file on disk, create a new instance.
                                _instance = ScriptableObject.CreateInstance<T>();
                            }
                            System.Diagnostics.Debug.Assert(_instance != null);
                        }
                    }
                }
                return _instance;
            }
        }

#if UNITY_EDITOR
        /// <summary>
        /// Returns the serialized object for the instance.
        /// </summary>
        /// <returns></returns>
        public UnityEditor.SerializedObject GetSerializedObject()
        {
            return new UnityEditor.SerializedObject(Instance);
        }
#endif
    }
}