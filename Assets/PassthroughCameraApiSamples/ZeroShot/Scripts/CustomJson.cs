using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace PassthroughCameraSamples.ZeroShot
{
    [Serializable]
    public class GeminiRoboticsPlanResponse
    {
        [JsonProperty("id")]
        public string Id { get; set; }

        [JsonProperty("plan")]
        public Plan Plan { get; set; }

        [JsonProperty("highlight_image_base64")]
        public string HighlightImageBase64 { get; set; }

        [JsonProperty("banana_image_base64")]
        public string BananaImageBase64 { get; set; }
    }

    [Serializable]
    public class Plan
    {
        [JsonProperty("goal")]
        public string Goal { get; set; }

        [JsonProperty("objects")]
        public List<PlanObject> Objects { get; set; }

        [JsonProperty("steps")]
        public List<PlanStep> Steps { get; set; }
    }

    [Serializable]
    public class PlanObject
    {
        [JsonProperty("label")]
        public string Label { get; set; }

        [JsonProperty("box_2d")]
        public List<int> Box2d { get; set; }
    }

    [Serializable]
    public class PlanStep
    {
        [JsonProperty("text")]
        public string Text { get; set; }

        [JsonProperty("object_label")]
        public string ObjectLabel { get; set; }
    }
}

