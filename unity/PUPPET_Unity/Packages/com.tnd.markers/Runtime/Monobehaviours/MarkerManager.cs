using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace TND.Markers
{
    public class MarkerManager : MonoBehaviour
    {
        // Singleton of the Marker Manager.
        private static MarkerManager s_instance;
        public static MarkerManager Instance
        {
            get
            {
                if (!s_instance)
                {
#if UNITY_2023_1_OR_NEWER
                    s_instance = FindAnyObjectByType<MarkerManager>();
#else
                    s_instance = FindObjectOfType<MarkerManager>();
#endif
                }
                return s_instance;
            }
        }

        // Camera used by the game.
        public Camera Camera;

        // References to scene objects.
        // Transform used by the player.
        public Transform Player;


        // Canvas on which to display UI.
        public Canvas Canvas
        {
            get; private set;
        }

        // Canvas Group which controls the alpha of the Canvas.
        public CanvasGroup CanvasGroup
        {
            get; private set;
        }

        // Dictionairies holding all placed markers and their gameobjects.
        private Dictionary<GameObject, MarkerController> _markers = new Dictionary<GameObject, MarkerController>(100);

        // Stored fade coroutine.
        private Coroutine _fadeCoroutine;

        // Check to see if we have a valid reference to the camera and Canvas..
        private void Update()
        {
            CheckForDependencies();
        }

        // Checks if the objects on which this manager depends are available, and if not, retrieves or creates them.
        private void CheckForDependencies()
        {
            if (Canvas == null)
            {
                try
                {
                    Canvas = GetComponentInChildren<Canvas>();
                    CanvasGroup = Canvas.GetComponent<CanvasGroup>();
                }
                catch
                {
                    Debug.LogError("[Markers] No Canvas found. Unable to set up Markers. This asset requires a Canvas and a Canvas Group to function. Please refer to the documentation for proper setup.");
                    enabled = false;
                }
            }
            if (Camera == null)
            {
                Debug.LogError("[Markers] No Camera component has been setup. Unable to set up Markers, ensure that a Camera component is referenced. Please refer to the documentation for proper setup.");
                CanvasGroup.alpha = 0;
                enabled = false;

            }
            if (Player == null)
            {
                Debug.LogError("[Markers] No Player reference has been setup. Unable to set up Markers, ensure that a Player location is referenced. Please refer to the documentation for proper setup.");
                CanvasGroup.alpha = 0;
                enabled = false;
            }
        }

        /// <summary>
        /// Spawn a marker with a static position as reference.
        /// </summary>
        internal MarkerController SpawnMarker(int markerInfo, string markerName, Transform position)
        {
            if (Canvas == null)
            {
                CheckForDependencies();
            }

            MarkerController _marker = Instantiate(MarkerSettings.Instance.MarkerTemplatePrefab, Canvas.transform).GetComponent<MarkerController>();
            _marker.SetMarker(markerInfo, markerName, position);
            _markers.Add(_marker.gameObject, _marker);
            return _marker;
        }

        /// <summary>
        /// Set the state of a specific marker.
        /// </summary>
        internal void SetMarkerState(GameObject marker, MarkerEnums.MarkerStates state)
        {
            _markers[marker].MarkerState = state;
        }

        /// <summary>
        /// Updates the state of a specific marker.
        /// </summary>
        internal void SetMarkerStateAndUpdate(GameObject marker, MarkerEnums.MarkerStates state, int markerInfo, string markerName, Transform position)
        {
            _markers[marker].MarkerState = state;

            _markers[marker].SetMarker(markerInfo, markerName, position);
        }

        /// <summary>
        /// Remove a specific marker.
        /// </summary>
        internal void RemoveMarker(GameObject marker)
        {
            if (_markers.ContainsKey(marker))
            {
                Destroy(_markers[marker].gameObject);
                _markers.Remove(marker);
            }
        }

        #region public API

        /// <summary>
        /// Set the Camera reference
        /// </summary>
        public void SetCamera(Camera camera)
        {
            Camera = camera;
        }

        /// <summary>
        /// Set the Player reference
        /// </summary>
        public void SetPlayer(Transform player)
        {
            Player = player;
        }

        /// <summary>
        /// Set the state for all markers.
        /// </summary>
        public void SetAllMarkerStates(MarkerEnums.MarkerStates state)
        {
            foreach (GameObject marker in _markers.Keys)
            {
                _markers[marker].MarkerState = state;
            }
        }



        /// <summary>
        /// Remove all markers.
        /// </summary>
        public void DestroyAllMarkers()
        {
            for (int i = _markers.Keys.Count(); i > 0; i++)
            {
                Destroy(_markers[_markers.Keys.ElementAt(i)].gameObject);
                _markers.Remove(_markers.Keys.ElementAt(i));
            }
        }

        /// <summary>
        /// Fades the Marker Canvas in.
        /// </summary>
        public void ShowCanvas()
        {
            if (_fadeCoroutine != null)
            {
                StopCoroutine(_fadeCoroutine);
            }
            _fadeCoroutine = StartCoroutine(FadeCanvas(true));
        }

        /// <summary>
        /// Fades the Marker Canvas out.
        /// </summary>
        public void HideCanvas()
        {
            if (_fadeCoroutine != null)
            {
                StopCoroutine(_fadeCoroutine);
            }
            _fadeCoroutine = StartCoroutine(FadeCanvas(false));
        }

        #endregion

        // Fades the Marker Canvas in and out.
        private IEnumerator FadeCanvas(bool fadeIn)
        {
            if (fadeIn)
            {
                while (CanvasGroup?.alpha < 1)
                {
                    CanvasGroup.alpha = Mathf.MoveTowards(CanvasGroup.alpha, 1, Time.deltaTime);
                    yield return null;
                }
            }
            else
            {
                while (CanvasGroup?.alpha > 0)
                {
                    CanvasGroup.alpha = Mathf.MoveTowards(CanvasGroup.alpha, 0, Time.deltaTime);
                    yield return null;
                }
            }
        }
    }
}
