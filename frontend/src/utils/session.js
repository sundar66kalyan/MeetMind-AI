export function getSessionId() {
  let sessionId = sessionStorage.getItem("meetmind_session_id");

  if (!sessionId) {
    sessionId = createSessionId();
    sessionStorage.setItem("meetmind_session_id", sessionId);
  }

  return sessionId;
}

export function createSessionId() {
  return `session-${crypto.randomUUID()}`;
}