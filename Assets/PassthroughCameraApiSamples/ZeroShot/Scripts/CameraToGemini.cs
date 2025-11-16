// Copyright (c) Meta Platforms, Inc. and affiliates.

using System;
using System.Collections;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Meta.WitAi.TTS.Interfaces;
using Meta.WitAi.TTS.Utilities;
using Meta.XR;
using Meta.XR.Samples;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.UI;

namespace PassthroughCameraSamples.ZeroShot
{
    [MetaCodeSample("PassthroughCameraApiSamples-CameraToWorld")]
    public class CameraToGemini : MonoBehaviour
    {
        [SerializeField] private PassthroughCameraAccess m_cameraAccess;
        [SerializeField] private Text m_debugText;
        [SerializeField] private RawImage m_image;
        [SerializeField] private string m_url = "https://flexible-loudly-polliwog.ngrok-free.app/";
        [SerializeField] private GameObject loadingIcon;
        private Texture2D m_cameraSnapshot;
        private GeminiRoboticsPlanResponse planResponse;
        private string currentGoalId = "";
        [SerializeField] private TTSSpeaker ttsSpeaker;
        public string dictationText = "";

        // Make this an async void method to allow awaiting the network request
        // In your CameraCanvas class (assuming it's a MonoBehaviour)
        public void MakeCameraSnapshot()
        {
            if (!m_cameraAccess.IsPlaying)
            {
                Debug.LogError("!m_cameraAccess.IsPlaying");
                return;
            }

            if (m_cameraSnapshot == null)
            {
                var size = m_cameraAccess.CurrentResolution;
                m_cameraSnapshot = new Texture2D(size.x, size.y, TextureFormat.RGBA32, false);
            }

            var pixels = m_cameraAccess.GetColors();
            m_cameraSnapshot.LoadRawTextureData(pixels);
            m_cameraSnapshot.Apply();
            m_debugText.text = "Waiting...";

            // 1. Stop streaming and immediately show the local snapshot
            StopCoroutine(ResumeStreamingFromCameraCor()); // Assuming this is managed elsewhere
            m_image.texture = m_cameraSnapshot;

            // 2. Start the coroutine to handle the web request and final texture update
            StartCoroutine(SendRequestAndUpdateTextureCoroutine(m_cameraSnapshot));
        }

        public void GoalSnapshot()
        {
            if (!m_cameraAccess.IsPlaying)
            {
                Debug.LogError("!m_cameraAccess.IsPlaying");
                return;
            }

            if (m_cameraSnapshot == null)
            {
                var size = m_cameraAccess.CurrentResolution;
                m_cameraSnapshot = new Texture2D(size.x, size.y, TextureFormat.RGBA32, false);
            }

            var pixels = m_cameraAccess.GetColors();
            m_cameraSnapshot.LoadRawTextureData(pixels);
            m_cameraSnapshot.Apply();
            m_debugText.text = "Waiting...";

            // 1. Stop streaming and immediately show the local snapshot
            StopCoroutine(ResumeStreamingFromCameraCor()); // Assuming this is managed elsewhere
            m_image.texture = m_cameraSnapshot;

            // 2. Start the coroutine to handle the web request and final texture update
            StartCoroutine(SendGoalAndUpdateTextureCoroutine(m_cameraSnapshot));
        }

        private IEnumerator SendGoalAndUpdateTextureCoroutine(Texture2D snapshot)
        {
            Debug.Log($"Starting network request Gemini for id: {currentGoalId}");
            // You could show a loading spinner UI here

            // Call the async method, which returns a Task immediately
            Task<Texture2D> textureTask = SendPutRequestAsync(snapshot, currentGoalId);

            // Wait until the task is completed. This pauses the coroutine
            // without blocking the main thread (the game).
            yield return new WaitUntil(() => textureTask.IsCompleted);

            Debug.Log($"Network request for Gemini completed for id: {currentGoalId}");

            // Now that the task is done, check for errors and get the result
            if (textureTask.IsFaulted)
            {
                Debug.LogError("Network request failed for Gemini: " + textureTask.Exception.Message);
                m_debugText.text = "You've completed all steps. Press A to start again.";
            }
            else
            {
                Texture2D highlightedTexture = textureTask.Result;
                if (highlightedTexture != null)
                {
                    Debug.Log("Request successful. Updating texture.");
                    m_image.texture = highlightedTexture;
                    m_debugText.text = planResponse.Plan.Steps[0].Text;
                    //ttsSpeaker.Speak(planResponse.Plan.Steps[0].Text);
                }
                else
                {
                    Debug.LogWarning("Request completed, but no highlight texture was returned. Gemini");
                    m_debugText.text = "You've completed all steps. Press A to start again.";
                }
            }

            // You could hide the loading spinner UI here
        }

        // In your CameraCanvas class
        private IEnumerator SendRequestAndUpdateTextureCoroutine(Texture2D snapshot)
        {
            Debug.Log($"Starting network request Gemini for id: {currentGoalId}");
            // You could show a loading spinner UI here

            // Call the async method, which returns a Task immediately
            Task<Texture2D> textureTask = SendPostRequestAsync(snapshot);

            // Wait until the task is completed. This pauses the coroutine
            // without blocking the main thread (the game).
            yield return new WaitUntil(() => textureTask.IsCompleted);

            Debug.Log($"Network request for Gemini completed for id: {currentGoalId}");

            // Now that the task is done, check for errors and get the result
            if (textureTask.IsFaulted)
            {
                Debug.LogError("Network request failed for Gemini: " + textureTask.Exception.Message);
                m_debugText.text = "You've completed all steps. Press A to start again.";
            }
            else
            {
                Texture2D highlightedTexture = textureTask.Result;
                if (highlightedTexture != null)
                {
                    Debug.Log("Request successful with Gemini. Updating texture.");
                    m_image.texture = highlightedTexture;
                    if(planResponse.Plan.Steps.Count > 0){ 
                        m_debugText.text = planResponse.Plan.Steps[0].Text;
                    }
                    else{ 
                        m_debugText.text = "You've completed all steps. Press A to start again."; 
                    }
                }
                else
                {
                    Debug.LogWarning("Request completed, but no highlight texture was returned. Gemini");
                    m_debugText.text = "You've completed all steps. Press A to start again.";
                }
            }

            // You could hide the loading spinner UI here
        }

        public void ResumeStreamingFromCamera()
        {
            StartCoroutine(ResumeStreamingFromCameraCor());
        }

        private IEnumerator ResumeStreamingFromCameraCor()
        {
            while (!m_cameraAccess.IsPlaying)
            {
                yield return null;
            }
            m_image.texture = m_cameraAccess.GetTexture();
            if (currentGoalId != "") m_debugText.text = "Press B once you are ready for next step..";
        }

        private IEnumerator Start()
        {
            m_debugText.text = "No permission granted.";
            while (!OVRPermissionsRequester.IsPermissionGranted(OVRPermissionsRequester.Permission.PassthroughCameraAccess))
            {
                yield return null;
            }
            m_debugText.text = "Press A to start your guided task.";

            while (!m_cameraAccess.IsPlaying)
            {
                yield return null;
            }
            ResumeStreamingFromCamera();
        }

        private Coroutine m_cameraUpdateCoroutine;

        private IEnumerator UpdateImageFromCamera()
        {
            // This loop will run until the coroutine is stopped
            while (true)
            {
                // Ensure the camera is playing before getting the texture
                if (m_cameraAccess.IsPlaying)
                {
                    m_image.texture = m_cameraAccess.GetTexture();
                }
                // Wait for the next frame
                yield return null;
            }
        }

        // This method now takes a texture, sends it, and returns the resulting texture from the response.
        public async Task<Texture2D> SendPostRequestAsync(Texture2D textureToSend)
        {
            using (HttpClient client = new HttpClient())
            {
                // Use the texture passed as a parameter
                byte[] imageBytes = XRImage.EncodeTexture(textureToSend, "image/png");
                string base64Image = Convert.ToBase64String(imageBytes);

                var payload = new
                {
                    prompt = dictationText,
                    image_base64 = base64Image
                };

                dictationText = ""; // Clear dictation text after sending

                string jsonContent = JsonConvert.SerializeObject(payload);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                // Add error handling for the web request
                try
                {
                    HttpResponseMessage response = await client.PostAsync(m_url, content);
                    response.EnsureSuccessStatusCode(); // Throws an exception if the response is not successful

                    string jsonString = await response.Content.ReadAsStringAsync();
                    planResponse = JsonConvert.DeserializeObject<GeminiRoboticsPlanResponse>(jsonString);
                    Debug.Log($"The first step in Gemini: {planResponse.Plan.Steps[0].Text}");
                    currentGoalId = planResponse.Id;

                    if (!string.IsNullOrEmpty(planResponse.HighlightImageBase64))
                    {
                        byte[] highlightImageBytes = Convert.FromBase64String(planResponse.HighlightImageBase64);
                        Texture2D highlightTexture = new Texture2D(2, 2);
                        if (highlightTexture.LoadImage(highlightImageBytes))
                        {
                            // Return the resulting texture instead of assigning it directly
                            return highlightTexture;
                        }
                        else
                        {
                            Debug.LogWarning("Failed to load highlight image from base64.");
                        }
                    }
                    else
                    {
                        Debug.LogWarning("HighlightImageBase64 is null or empty.");
                    }
                }
                catch (HttpRequestException e)
                {
                    Debug.LogError($"Request error: {e.Message}");
                }

                // Return null if the process fails at any point
                return null;
            }
        }

        public async Task<Texture2D> SendPutRequestAsync(Texture2D textureToSend, string id)
        {
            using (HttpClient client = new HttpClient())
            {
                // Use the texture passed as a parameter
                byte[] imageBytes = XRImage.EncodeTexture(textureToSend, "image/png");
                string base64Image = Convert.ToBase64String(imageBytes);

                var payload = new
                {
                    prompt = dictationText,
                    image_base64 = base64Image
                };

                dictationText = ""; // Clear dictation text after sending

                string jsonContent = JsonConvert.SerializeObject(payload);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                // Add error handling for the web request
                try
                {
                    HttpResponseMessage response = await client.PutAsync(m_url + "goals/" + id, content);
                    response.EnsureSuccessStatusCode(); // Throws an exception if the response is not successful

                    string jsonString = await response.Content.ReadAsStringAsync();
                    planResponse = JsonConvert.DeserializeObject<GeminiRoboticsPlanResponse>(jsonString);
                    Debug.Log($"The next step is: {planResponse.Plan.Steps[0].Text}");

                    if (!string.IsNullOrEmpty(planResponse.HighlightImageBase64))
                    {
                        byte[] highlightImageBytes = Convert.FromBase64String(planResponse.HighlightImageBase64);
                        Texture2D highlightTexture = new Texture2D(2, 2);
                        if (highlightTexture.LoadImage(highlightImageBytes))
                        {
                            // Return the resulting texture instead of assigning it directly
                            return highlightTexture;
                        }
                        else
                        {
                            Debug.LogWarning("Failed to load highlight image from base64.");
                        }
                    }
                    else
                    {
                        Debug.LogWarning("HighlightImageBase64 is null or empty.");
                    }
                }
                catch (HttpRequestException e)
                {
                    Debug.LogError($"Request error: {e.Message}");
                }

                // Return null if the process fails at any point
                return null;
            }
        }
    }
}