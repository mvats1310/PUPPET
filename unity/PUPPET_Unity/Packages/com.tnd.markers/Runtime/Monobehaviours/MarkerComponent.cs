using System;
using UnityEngine;

namespace TND.Markers
{
    public class MarkerComponent : MonoBehaviour
    {
        [Header("Marker Component")]
        public int MarkerType = 0;
        public string MarkerName = "Default";

        //Cache
        private int _prefMarkerType;
        private string _prefMarkerName;

        // Internal references
        private MarkerController _thisMarkerController;
        private MarkerManager _thisMarkerManager;

        private void OnDestroy()
        {
            DeleteMarker();
        }

        private void OnDisable()
        {
            DeleteMarker();
        }

        private void OnEnable()
        {
            ValidateMarkerType();

            _prefMarkerType = MarkerType;
            _prefMarkerName = MarkerName;

            _thisMarkerManager = MarkerManager.Instance;
            if (enabled && gameObject.activeInHierarchy)
            {

                MakeMarker();
            }
        }

        private void Update()
        {
            if (_prefMarkerType != MarkerType || _prefMarkerName != MarkerName)
            {
                _prefMarkerType = MarkerType;
                _prefMarkerName = MarkerName;

                MakeMarker();
            }
        }

        private void MakeMarker()
        {
            if (!_thisMarkerController)
            {
                _thisMarkerController = _thisMarkerManager.SpawnMarker(MarkerType, MarkerName, transform);
            }
            else
            {
                _thisMarkerManager?.SetMarkerStateAndUpdate(_thisMarkerController.gameObject, MarkerEnums.MarkerStates.Active, MarkerType, MarkerName, transform);
            }
        }

        private void DeleteMarker()
        {
            if (_thisMarkerController)
            {
                _thisMarkerManager?.SetMarkerState(_thisMarkerController.gameObject, MarkerEnums.MarkerStates.Destroy);
            }
        }

        public void ValidateMarkerType()
        {
            if (MarkerType == MarkerSettings.Instance.MarkerTypes.Count)
            {
                Debug.LogError("[Markers] " + name + " had an invalid Marker Type Selected! " + MarkerType);
                MarkerType = 0;
            }
        }

        #region public API

        /// <summary>
        /// Change the MarkerType
        /// </summary>
        public void SetMarkerType(int markerType)
        {
            MarkerType = markerType;
        }

        /// <summary>
        /// Change the MarkerType
        /// </summary>
        public void SetMarkerName(string markerName)
        {
            MarkerName = markerName;
        }

        #endregion
    }
}
