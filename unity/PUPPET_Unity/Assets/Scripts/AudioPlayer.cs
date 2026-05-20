using System;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.AudioCommon;
using UnityEngine.InputSystem;
using UnityEngine.UI;
using NAudio.Wave;
using NLayer.NAudioSupport;
using System.IO;

public class AudioPlayer : MonoBehaviour
{
    private ROSConnection ros;

    public AudioSource audioSource = null;
    public InputActionReference enableSpeakerReference = null;
    public RawImage iconOn = null;
    public RawImage iconOff = null;
    public bool speakerEnabled = false;
    public string topicName = "/audio_in/audio";
    public int samples = 100000;
    public int depth = 16;
    public int channels = 2;
    public int frequency = 44100;
    public bool littleEndian = true;
    public bool signed = true;
    public bool compressed = true;

    private byte[] mp3buffer = new byte[16384 * 4]; // needs to be big enough to hold a decompressed MP3 frame
    private byte[] byteBuffer = new byte[16384 * 4];
    private IMp3FrameDecompressor decompressor;
    private BufferedWaveProvider bufferedWaveProvider;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<AudioDataMsg>(topicName, AudioCallback);

        iconOff.enabled = !speakerEnabled;
        iconOn.enabled = speakerEnabled;

        if (!compressed)
        {
            bufferedWaveProvider = new BufferedWaveProvider(new WaveFormat(frequency, depth, channels));
        }

        audioSource.clip = AudioClip.Create("ROSAudioPlayer", samples, channels, frequency, true, OnAudioRead);
    }

    private void Awake()
    {
        enableSpeakerReference.action.performed += OnButtonPress;
    }

    private void OnApplicationQuit()
    {
        enableSpeakerReference.action.performed -= OnButtonPress;

        if (audioSource.isPlaying)
        {
            audioSource.Stop();
        }
    }

    void OnButtonPress(InputAction.CallbackContext context)
    {
        if (!speakerEnabled)
        {
            bufferedWaveProvider?.ClearBuffer();
            audioSource.Play();
            Debug.Log("Speaker enabled");
        }
        else
        {
            audioSource.Stop();
            Debug.Log("Speaker disabled");
        }

        speakerEnabled = !speakerEnabled;
        iconOff.enabled = !speakerEnabled;
        iconOn.enabled = speakerEnabled;
    }

    void OnAudioRead(float[] data)
    {
        if (bufferedWaveProvider != null)
        {
            if (compressed)
            {
                bufferedWaveProvider.Read(byteBuffer, 0, data.Length * 4);

                for (int i = 0; i < data.Length; i++)
                {
                    data[i] = BitConverter.ToSingle(byteBuffer, i * 4);
                }
            }
            else
            {
                bufferedWaveProvider.Read(byteBuffer, 0, data.Length * 2);
                Convert16BitByteArrayToAudioClipData(byteBuffer, data);
            }
        }
    }

    void AudioCallback(AudioDataMsg msg)
    {
        if (speakerEnabled)
        {
            if (compressed)
            {
                var frame = Mp3Frame.LoadFromStream(new MemoryStream(msg.data));

                if (frame != null)
                {
                    if (decompressor == null)
                    {
                        decompressor = CreateFrameDecompressor(frame);
                        bufferedWaveProvider = new BufferedWaveProvider(decompressor.OutputFormat);
                    }

                    int decompressed = decompressor.DecompressFrame(frame, mp3buffer, 0);
                    bufferedWaveProvider.AddSamples(mp3buffer, 0, decompressed);
                }
            }
            else
            {
                bufferedWaveProvider.AddSamples(msg.data, 0, msg.data.Length);
            }
        }
    }

    void Update()
    {
        if (speakerEnabled && !audioSource.isPlaying)
        {
            audioSource.Play();
        }
    }

    private static IMp3FrameDecompressor CreateFrameDecompressor(Mp3Frame frame)
    {
        int _channels = frame.ChannelMode == ChannelMode.Mono ? 1 : 2;
        WaveFormat waveFormat = new Mp3WaveFormat(frame.SampleRate, _channels, frame.FrameLength, frame.BitRate);
        return new Mp3FrameDecompressor(waveFormat);
    }

    private void Convert16BitByteArrayToAudioClipData(byte[] source, float[] dest)
    {
        // https://stackoverflow.com/a/65091830
        // https://stackoverflow.com/q/16078254

        int bytes = depth / 8;
        float negativeDepth = Mathf.Pow(2f, depth - 1f);
        float positiveDepth = negativeDepth - 1f;

        for (int i = 0; i < dest.Length; i++)
        {
            if (littleEndian ^ BitConverter.IsLittleEndian)
            {
                Array.Reverse(source, i * bytes, bytes);
            }

            float rawSample, sampleDepth;

            switch (depth)
            {
                case 8:
                    rawSample = source[i];
                    break;
                case 16:
                    rawSample = BitConverter.ToInt16(source, i * bytes);
                    break;
                case 32:
                    rawSample = BitConverter.ToInt32(source, i * bytes);
                    break;
                default:
                    throw new ArgumentOutOfRangeException(nameof(depth), depth, "Supported values are: 8, 16, 32");
            }

            if (signed)
            {
                sampleDepth = (rawSample < 0 ? negativeDepth : positiveDepth);
            }
            else
            {
                sampleDepth = negativeDepth * 2;
            }

            dest[i] = rawSample / sampleDepth;

            // alternative (slightly incorrect):
            // dest[i] = rawSample / Int16.MaxValue;
            // where negativeDepth = 32768 and positiveDepth = Int16.MaxValue = 32767
        }
    }
}
