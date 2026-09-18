export const API_BASE_URL = "https://meetmind-ai-b74u.onrender.com";

export async function askAI(question, sessionId = "frontend-demo") {
  const response = await fetch(`${API_BASE_URL}/api/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      session_id: sessionId,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to get AI response");
  }

  return data;
}

export async function clearConversation(sessionId = "frontend-demo") {
  const response = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}`,
    {
      method: "DELETE",
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to clear conversation");
  }

  return data;
}

export async function getSession(sessionId = "frontend-demo") {
  const response = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}`
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to get session");
  }

  return data;
}

export async function getAPIStatus() {
  const response = await fetch(`${API_BASE_URL}/api/status`);

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to get API status");
  }

  return data;
}

export async function uploadPDF(file) {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(
    `${API_BASE_URL}/api/upload-pdf`,
    {
      method: "POST",
      body: formData,
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to upload PDF"
    );
  }

  return data;
}

export async function transcribeAudio(audioBlob) {
  const formData = new FormData();

  formData.append(
    "file",
    audioBlob,
    "meeting_audio.webm"
  );

  const response = await fetch(
    `${API_BASE_URL}/api/transcribe-audio`,
    {
      method: "POST",
      body: formData,
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to transcribe audio"
    );
  }

  return data;
}
export const WS_BASE_URL =
  API_BASE_URL.replace("https://", "wss://").replace("http://", "ws://");

export function createLiveSessionSocket(sessionId) {
  return new WebSocket(`${WS_BASE_URL}/api/ws/${sessionId}`);
}
