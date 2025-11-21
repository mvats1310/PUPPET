using UnityEngine;
using UnityEngine.UI;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;

public class ImageSubscriber : MonoBehaviour
{
    private ROSConnection ros;

    public RawImage screen = null;
    public string topicName = "/xtion/rgb/image_raw";
    public bool compressed = true;
    public bool usingBGR = true;

    private Texture2D texture;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();

        if (compressed)
        {
            ros.Subscribe<CompressedImageMsg>(topicName + "/compressed", CompressedImageCallback);
        }
        else
        {
            ros.Subscribe<ImageMsg>(topicName, ImageCallback);

            // for some reason, uncompressed frames are flipped vertically
            var temp = screen.rectTransform.localScale;
            temp.y *= -1;
            screen.rectTransform.localScale = temp;
        }

        texture = new Texture2D(1, 1);
        screen.texture = texture;
    }

    private void OnApplicationQuit()
    {
        if (compressed)
        {
            ros.Unsubscribe(topicName + "/compressed");
        }
        else
        {
            ros.Unsubscribe(topicName);
        }
    }

    void CompressedImageCallback(CompressedImageMsg msg)
    {
        texture.LoadImage(msg.data);
    }

    void ImageCallback(ImageMsg msg)
    {
        // https://discussions.unity.com/t/how-to-place-ros-image-messages-in-scene-and-view-in-hmd/885576/2
        var texture = new Texture2D((int)msg.width, (int)msg.height, TextureFormat.RGB24, false);

        if (usingBGR)
        {
            BgrToRgb(msg.data);
        }
        
        texture.LoadRawTextureData(msg.data);
        texture.Apply();
        screen.texture = texture;
    }
    public void BgrToRgb(byte[] data)
    {
        for (int i = 0; i < data.Length; i += 3)
        {
            byte dummy = data[i];
            data[i] = data[i + 2];
            data[i + 2] = dummy;
        }
    }
}
