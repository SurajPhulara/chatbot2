// src/api.js
import axios from 'axios';

const API_URL = 'https://api.openai.com/v1/chat/completions';

export const callOpenAiApi = async (chatHistory, currentJson) => {
  const apiKey = process.env.REACT_APP_OPENAI_API_KEY;

  const query = `Your query here`; // Adapt your query as needed

  try {
    const response = await axios.post(
      API_URL,
      {
        model: "gpt-3.5-turbo", // Adjust as necessary
        messages: chatHistory,
        max_tokens: 4000
      },
      {
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const updatedJson = response.data;

    // Update current JSON with new answers
    if (updatedJson.inferences) {
      updatedJson.inferences.forEach((update) => {
        currentJson[update.field_name] = update.answer;
      });
    }

    return { updatedJson: currentJson, nextReply: updatedJson.next_reply };
  } catch (error) {
    console.error("Error calling OpenAI API:", error);
    return { updatedJson: currentJson, nextReply: "" };
  }
};
