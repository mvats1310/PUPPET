using System;
using System.Linq;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using Unity.VisualScripting;
using RosMessageTypes.AudioCommon;
using UnityEngine.InputSystem;
using UnityEngine.UI;

public class AudioRecorder : MonoBehaviour
{
    private ROSConnection ros;

    public string topicName = "/audio_out/audio";
    public InputActionReference enableMicrophoneReference = null;
    public RawImage iconOn = null;
    public RawImage iconOff = null;
    public bool micEnabled = false;
    public int depth = 16;
    public int frequency = 16000;
    public bool littleEndian = true;
    public bool signed = true;

    private AudioClip mic;
    private bool micConnected = false;
    private int lastPosition;
    private string deviceName;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<AudioDataMsg>(topicName, 1);

        if (Microphone.devices.Length <= 0)
        {
            Debug.LogWarning("Microphone not connected!");
            micEnabled = false;
        }
        else
        {
            Debug.Log($"Got {Microphone.devices.Length} microphone device(s):");

            foreach (var device in Microphone.devices)
            {
                Debug.Log(device);
            }

            deviceName = Microphone.devices.Where(d => d.ContainsInsensitive("oculus")).FirstOrDefault();

            if (deviceName != null)
            {
                Debug.Log($"Using microphone device: {deviceName}");
            }
            else
            {
                Debug.Log($"Using default microphone device");
            }

            int minFrequency, maxFrequency;
            Microphone.GetDeviceCaps(deviceName, out minFrequency, out maxFrequency);

            if (minFrequency == 0 && maxFrequency == 0)
            {
                // the device supports any frequency 
            }
            else if (frequency < minFrequency || frequency > maxFrequency)
            {
                Debug.LogWarning($"Target microphone frequency {frequency} not in supported range: [{minFrequency},{maxFrequency}]");
            }

            micConnected = true;
            mic = Microphone.Start(deviceName, true, 1, frequency);

            enableMicrophoneReference.action.performed += OnButtonPress;
        }

        iconOff.enabled = !micEnabled;
        iconOn.enabled = micEnabled;
    }

    private void OnApplicationQuit()
    {
        if (micConnected)
        {
            enableMicrophoneReference.action.performed -= OnButtonPress;
            Microphone.End(deviceName);
        }
    }

    void OnButtonPress(InputAction.CallbackContext context)
    {
        if (micConnected)
        {
            Debug.Log(micEnabled ? "Microphone disabled" : "Microphone enabled");
            micEnabled = !micEnabled;
            iconOff.enabled = !micEnabled;
            iconOn.enabled = micEnabled;
        }
    }

    void Update()
    {
        if (micConnected && micEnabled)
        {
            // https://stackoverflow.com/q/55779470
            // https://stackoverflow.com/a/61267482

            if (!Microphone.IsRecording(deviceName))
            {
                // this takes several frames to execute and therefore makes the app freeze; it would
                // be best to place this on its own thread, but it's not supposed to happen anyway
                mic = Microphone.Start(deviceName, true, 1, frequency);
                Debug.LogWarning("Microphone stopped recording and was enabled again.");
            }

            int position = Microphone.GetPosition(deviceName);

            if (position > 0)
            {
                if (lastPosition > position)
                {
                    lastPosition = 0;
                }

                if (position - lastPosition > 0)
                {
                    float[] samples = new float[(position - lastPosition) * mic.channels];
                    mic.GetData(samples, lastPosition);
                    byte[] data = ConvertAudioClipDataTo16BitByteArray(samples);
                    ros.Publish(topicName, new AudioDataMsg(data));
                    lastPosition = position;
                }
            }
        }
    }

    private byte[] ConvertAudioClipDataTo16BitByteArray(float[] source)
    {
        // https://stackoverflow.com/a/65091830
        // https://stackoverflow.com/questions/16078254/create-audioclip-from-byte

        int bytes = depth / 8;
        float negativeDepth = Mathf.Pow(2f, depth - 1f);
        float positiveDepth = negativeDepth - 1f;

        byte[] data = new byte[source.Length * bytes];

        for (int i = 0; i < source.Length; i++)
        {
            float rawSample, sampleDepth;

            if (signed)
            {
                rawSample = source[i];
                sampleDepth = (rawSample < 0 ? negativeDepth : positiveDepth);
            }
            else
            {
                rawSample = source[i] + 1.0f;
                sampleDepth = negativeDepth * 2;
            }

            float scaledSample = rawSample * sampleDepth;

            byte[] array;

            switch (depth)
            {
                case 8:
                    array = BitConverter.GetBytes((Byte)scaledSample);
                    break;
                case 16:
                    array = BitConverter.GetBytes((Int16)scaledSample);
                    break;
                case 32:
                    array = BitConverter.GetBytes((Int32)scaledSample);
                    break;
                default:
                    throw new ArgumentOutOfRangeException(nameof(depth), depth, "Supported values are: 8, 16, 32");
            }

            if (littleEndian ^ BitConverter.IsLittleEndian)
            {
                Array.Reverse(array, i * bytes, bytes);
            }

            Array.Copy(array, 0, data, i * bytes, bytes);
        }

        return data;
    }
}
