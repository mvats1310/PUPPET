using UnityEngine;
using UnityEngine.UI;

namespace TND.Markers
{
    [RequireComponent(typeof(CanvasGroup))]
    [RequireComponent(typeof(RectTransform))]
    [DefaultExecutionOrder(9999)]
    public class MarkerController : MonoBehaviour
    {
        // Public references to components of the marker.
        [Tooltip("Icon of the _markerInformation.")]
        public Image MarkerIcon;

        [Tooltip("Directional arrow of the _markerInformation, shows the target when it is off-screen.")]
        public GameObject MarkerArrowParent;
        public Image MarkerArrowIcon;

        [Tooltip("Name of the Objective or Quest related to the _markerInformation.")]
        public Text MarkerName;

        [Tooltip("Distance to the _markerInformation from the player.")]
        public Text MarkerDistance;

        [SerializeField, ReadOnly]
        public MarkerEnums.MarkerStates MarkerState = MarkerEnums.MarkerStates.Active;

        [SerializeField, ReadOnly]
        private MarkerEnums.MarkerRanges _markerRange;

        // Private references to components of the marker.
        private CanvasGroup _canvasGroup;
        private RectTransform _rect;

        // Marker information and references.
        private MarkerType _markerInformation;
        private Transform _markerTransform;

        private Vector3 _targetPosition;
        private Vector3 _inversedTargetPosition;

        // Screen properties,
        private Vector3 _screenHalf;
        private Vector3 _screenCenter;

        // Marker properties.
        private Vector3 _positionX;
        private Vector3 _positionY;
        private float _angle;
        private float _distance;
        private int _currentDistance;
        private bool _onScreen;

        // Marker script references
        private MarkerManager _thisMarkerManager;
        private MarkerSettings _thisMarkerSettings;

        // Here we set the marker script references,  canvas group and rect.
        private void Awake()
        {
            _thisMarkerManager = MarkerManager.Instance;
            _thisMarkerSettings = MarkerSettings.Instance;
            _canvasGroup = GetComponent<CanvasGroup>();
            _rect = GetComponent<RectTransform>();

            if (_canvasGroup == null)
            {
                Debug.LogError("[Markers] Marker Controller is missing a Canvas Group. Please ensure the Marker prefab has a Canvas Group");
            }
        }

        // Set the target and related information of the marker.
        internal void SetMarker(int markerInfo, string markerName, Transform position)
        {
            // Receiving and setting parameters.
            _markerInformation = _thisMarkerSettings.MarkerTypes[markerInfo];
            _markerTransform = position;

            if (MarkerName != null)
            {
                MarkerName.text = markerName;
            }

            if (_markerInformation.Visual)
            {
                if (MarkerIcon != null)
                {
                    MarkerIcon.sprite = Sprite.Create(_markerInformation.Visual, new Rect(Vector2.zero, new Vector2(_markerInformation.Visual.width, _markerInformation.Visual.height)), new Vector2(0.5f, 0.5f));
                    MarkerIcon.sprite.name = "Marker Sprite";
                }
            }

            if (_markerInformation.OffscreenArrowVisual)
            {
                if (MarkerArrowIcon != null)
                {
                    MarkerArrowIcon.sprite = Sprite.Create(_markerInformation.OffscreenArrowVisual, new Rect(Vector2.zero, new Vector2(_markerInformation.OffscreenArrowVisual.width, _markerInformation.OffscreenArrowVisual.height)), new Vector2(0.5f, 0.5f));
                    MarkerArrowIcon.sprite.name = "Marker Arrow Sprite";
                }
            }
        }

        // Calculate position, distance, visibility and arrow rotation.
        private void LateUpdate()
        {
            if (_thisMarkerManager.Camera != null && _markerTransform)
            {
                _targetPosition = _thisMarkerManager.Camera.WorldToScreenPoint(_markerTransform.position);
            }

            if (Mathf.Approximately(_targetPosition.z, 0))
            {
                return;
            }

            _screenHalf = new Vector3(Screen.width, Screen.height) / 2;
            _screenCenter = new Vector3(_targetPosition.x, _targetPosition.y, 0) - _screenHalf;

            if (_targetPosition.z < 0)
            {
                _screenCenter *= -1;
            }


            _onScreen = IsOnScreen();

            if (MarkerState == MarkerEnums.MarkerStates.Destroy && _canvasGroup.alpha == 0)
            {
                _thisMarkerManager.RemoveMarker(gameObject);
                return;
            }

            if (MarkerState == MarkerEnums.MarkerStates.Unactive && _canvasGroup.alpha == 0)
            {
                return;
            }

            if (MarkerName != null)
            {
                if (_markerInformation.DisplayName && _markerInformation.DisplayName && _onScreen)
                {
                    if (!MarkerName.gameObject.activeSelf)
                    {
                        MarkerName.gameObject.SetActive(true);
                    }
                }
                else if (_onScreen)
                {
                    if (MarkerName.gameObject.activeSelf)
                    {
                        MarkerName.gameObject.SetActive(false);
                    }
                }
            }

            if (MarkerDistance != null)
            {
                if (_markerInformation.DisplayDistance && _markerInformation.DisplayDistance && _onScreen)
                {
                    if (!MarkerDistance.gameObject.activeSelf)
                    {
                        MarkerDistance.gameObject.SetActive(true);
                    }
                    if (_currentDistance != (int)_distance)
                    {
                        _currentDistance = (int)_distance;
                        MarkerDistance.text = _currentDistance + _markerInformation.DistanceSuffix;
                    }
                }
                else if (_onScreen)
                {
                    if (MarkerDistance.gameObject.activeSelf)
                    {
                        MarkerDistance.gameObject.SetActive(false);
                    }
                }
            }

            if (MarkerState == MarkerEnums.MarkerStates.Active)
            {
                if (IsInRange() && _onScreen)
                {
                    _canvasGroup.alpha = Mathf.MoveTowards(_canvasGroup.alpha, 0.85f, Time.deltaTime);
                }
                else if (IsInRange() && !_onScreen)
                {
                    _canvasGroup.alpha = Mathf.MoveTowards(_canvasGroup.alpha, 0.5f, Time.deltaTime);
                }
                else
                {
                    _canvasGroup.alpha = Mathf.MoveTowards(_canvasGroup.alpha, 0, Time.deltaTime);
                }
            }

            if (!_onScreen)
            {
                _screenCenter = _screenCenter.normalized;

                if (_screenCenter.x == 0)
                {
                    _screenCenter.x = 0.1f;
                }

                if (_screenCenter.y == 0)
                {
                    _screenCenter.y = 0.1f;
                }

                _positionX = _screenCenter * (_screenHalf.x / Mathf.Abs(_screenCenter.x));
                _positionY = _screenCenter * (_screenHalf.y / Mathf.Abs(_screenCenter.y));

                if (_positionX.sqrMagnitude < _positionY.sqrMagnitude)
                {
                    _targetPosition = _screenHalf + _positionX;
                }
                else
                {
                    _targetPosition = _screenHalf + _positionY;
                }

                if (MarkerArrowParent != null)
                {
                    if (_markerInformation.DisplayOffscreenArrow && _markerInformation.DisplayOffscreenArrow)
                    {
                        if (!MarkerArrowParent.activeSelf)
                        {
                            MarkerArrowParent.SetActive(true);
                        }
                        if (_thisMarkerManager.Camera != null)
                        {
                            _inversedTargetPosition = _thisMarkerManager.Camera.transform.InverseTransformPoint(_markerTransform.position);
                        }
                        _angle = -Mathf.Atan2(_inversedTargetPosition.x, _inversedTargetPosition.y) * Mathf.Rad2Deg - 180;
                        MarkerArrowParent.transform.eulerAngles = new Vector3(0.0f, 0.0f, _angle);
                    }
                    else
                    {
                        if (MarkerArrowParent.activeSelf)
                        {
                            MarkerArrowParent.SetActive(false);
                        }

                    }
                }

                if (MarkerName != null)
                {
                    if (_markerInformation.DisplayName && _markerInformation.OffscreenNameFadeout)
                    {
                        if (MarkerName.gameObject.activeSelf)
                        {
                            MarkerName.gameObject.SetActive(false);
                        }
                    }
                }

                if (MarkerDistance != null)
                {
                    if (_markerInformation.DisplayDistance && _markerInformation.OffscreenDistanceFadeout)
                    {
                        if (MarkerDistance.gameObject.activeSelf)
                        {
                            MarkerDistance.gameObject.SetActive(false);
                        }
                    }
                }
            }
            else
            {
                if (MarkerArrowParent != null)
                {
                    if (MarkerArrowParent.activeSelf)
                    {
                        MarkerArrowParent.SetActive(false);
                    }
                }
            }

            float scaleFactor = 1;
            if (_thisMarkerManager.Canvas)
            {
                scaleFactor = _thisMarkerManager.Canvas.scaleFactor;
            }

            Vector2 sizeInPixels = _rect.sizeDelta * scaleFactor * 0.65f;//manual scale offset

            float clampedX = Mathf.Clamp(_targetPosition.x, sizeInPixels.x, Screen.width - sizeInPixels.x);
            float clampedY = Mathf.Clamp(_targetPosition.y, sizeInPixels.y, Screen.height - sizeInPixels.y);
            transform.position = new Vector3(clampedX, clampedY, 0);

            if (MarkerState == MarkerEnums.MarkerStates.Unactive || MarkerState == MarkerEnums.MarkerStates.Destroy)
            {
                _canvasGroup.alpha = Mathf.MoveTowards(_canvasGroup.alpha, 0, Time.deltaTime);
            }
        }

        // Is the marker position currently on screen?
        private bool IsOnScreen()
        {
            if (_targetPosition.x > Screen.width || _targetPosition.x < 0 || _targetPosition.y > Screen.height || _targetPosition.y < 0 || _targetPosition.z < 0)
            {
                return false;
            }
            else
            {
                return true;
            }
        }

        // Is the marker distance within the minimum and maximum range?
        private bool IsInRange()
        {
            _distance = Distance;
            if (_distance >= _markerInformation.MinimumDistance && Distance <= _markerInformation.MaximumDistance)
            {
                return true;
            }
            else
            {
                return false;
            }
        }

        // Get the distance from the player to the marker position.
        private float Distance
        {
            get
            {
                if (_thisMarkerManager.Player != null)
                {
                    return Vector3.Distance(_markerTransform.position, _thisMarkerManager.Player.position);
                }
                else
                {
                    return 0;
                }
            }
        }
    }
}
