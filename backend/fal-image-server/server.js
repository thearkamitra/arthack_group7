
require("dotenv").config();

const express = require("express");
const { fal } = require("@fal-ai/client");

const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

if (process.env.FAL_KEY) {
  fal.config({ credentials: process.env.FAL_KEY });
}

app.get("/", (req, res) => {
  res.json({ message: "fal.ai image server is running" });
});

app.post("/generate-image", async (req, res) => {
  try {
    const prompt = req.body?.prompt;

    if (typeof prompt !== "string" || !prompt.trim()) {
      return res.status(400).json({
        error: "Please provide a non-empty prompt string."
      });
    }

    if (!process.env.FAL_KEY) {
      return res.status(500).json({
        error: "FAL_KEY is missing. Please configure it in the server .env file."
      });
    }

    const result = await fal.subscribe("fal-ai/z-image/base", {
      input: {
        prompt: prompt.trim()
      },
      logs: true
    });

    const imageUrl = result.data?.images?.[0]?.url;

    if (!imageUrl) {
      console.error("Unexpected fal.ai response:", result);
      return res.status(502).json({
        error: "fal.ai returned no image URL."
      });
    }

    res.json({ imageUrl });
  } catch (error) {
    console.error("Image generation failed:", error);
    res.status(500).json({
      error: error.message || "Image generation failed."
    });
  }
});

app.listen(port, () => {
  console.log(`fal.ai image server listening at http://localhost:${port}`);
});
