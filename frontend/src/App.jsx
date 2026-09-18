import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Document, Page, pdfjs } from "react-pdf";
import {
  askAI,
  clearConversation,
  getAPIStatus,
  uploadPDF,
  transcribeAudio,
} from "./services/api";
import { getSessionId } from "./utils/session";
import "./App.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [answerSource, setAnswerSource] = useState("");
  const [webResults, setWebResults] = useState([]);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [speechError, setSpeechError] = useState("");
  const [audioCaptureStatus, setAudioCaptureStatus] = useState("");
  const [meetingAudioStream, setMeetingAudioStream] = useState(null);
  const [audioRecordingStatus, setAudioRecordingStatus] = useState("");
  const [isAutoTranscribing, setIsAutoTranscribing] = useState(false);
  const [audioDownloadUrl, setAudioDownloadUrl] = useState("");
  const [detectedQuestion, setDetectedQuestion] = useState("");
  const lastAutoQuestion = useRef("");
  const autoTranscribingRef = useRef(false);
  const [loading, setLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [sessionId] = useState(() => getSessionId());
  const [pdfUrl, setPdfUrl] = useState("");
  const [highlights, setHighlights] = useState([]);
  const [relevantBlock, setRelevantBlock] = useState(null);
  const [relevantLine, setRelevantLine] = useState(null);
  const [pdfFile, setPdfFile] = useState(null);
  const [pdfUploading, setPdfUploading] = useState(false);
  const [pdfStatus, setPdfStatus] = useState("");

  useEffect(() => {
    const checkBackend = async () => {
      try {
        await getAPIStatus();
        setBackendOnline(true);
      } catch (error) {
        setBackendOnline(false);
      }
    };

    checkBackend();

    const interval = setInterval(checkBackend, 10000);

    return () => clearInterval(interval);
  }, []);

  const handleAskAI = async () => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      return;
    }

    setLoading(true);
    setAnswer("");

    try {
      const data = await askAI(trimmedQuestion, sessionId);

      setAnswer(data.answer);
      setAnswerSource(data.source || "");
      setWebResults(data.results || []);
      setHighlights(data.highlights || []);
      setRelevantBlock(data.relevant_block || null);
      setRelevantLine(data.relevant_line || null);
      setBackendOnline(true);
    } catch (error) {
      setAnswer(`Error: ${error.message}`);
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  };

  const handlePDFUpload = async () => {
    if (!pdfFile) {
      setPdfStatus("Please select a PDF file.");
      return;
    }

    setPdfUploading(true);
    setPdfStatus("");

    try {
      const data = await uploadPDF(pdfFile);

      setPdfUrl(
        `http://127.0.0.1:8000${data.pdf_url}`
      );

      setPdfStatus(
        `Uploaded: ${data.filename} | Pages: ${data.pages} | Chunks: ${data.chunks}`
      );

      setBackendOnline(true);
    } catch (error) {
      setPdfStatus(
        `Upload failed: ${error.message}`
      );
    } finally {
      setPdfUploading(false);
    }
  };

  const handleClearConversation = async () => {
    try {
      await clearConversation(sessionId);
      setQuestion("");
      setAnswer("");
      setAnswerSource("");
      setWebResults([]);
      setHighlights([]);
      setRelevantBlock(null);
      setRelevantLine(null);
    } catch (error) {
      setAnswer(`Error: ${error.message}`);
    }
  };

  const processDetectedQuestion = async (spokenText) => {
    const detectedQuestion = spokenText.trim();

    if (!detectedQuestion) return;

    const lowerText = detectedQuestion.toLowerCase();

    const questionStarters = [
      "what ",
      "who ",
      "when ",
      "where ",
      "which ",
      "why ",
      "how ",
      "can ",
      "could ",
      "does ",
      "do ",
      "is ",
      "are ",
      "was ",
      "were ",
    ];

    const looksLikeQuestion =
      detectedQuestion.endsWith("?") ||
      questionStarters.some((starter) =>
        lowerText.startsWith(starter)
      );

    if (!looksLikeQuestion) return;

    if (detectedQuestion === lastAutoQuestion.current) {
      return;
    }

    lastAutoQuestion.current = detectedQuestion;

    setDetectedQuestion(detectedQuestion);
    setLoading(true);
    setAnswer("");
    setAnswerSource("");
    setWebResults([]);

    try {
      const data = await askAI(
        detectedQuestion,
        sessionId
      );

      setAnswer(data.answer || "");
      setAnswerSource(data.source || "");
      setWebResults(data.results || []);
      setHighlights(data.highlights || []);
      setRelevantBlock(data.relevant_block || null);
      setRelevantLine(data.relevant_line || null);
      setBackendOnline(true);
    } catch (error) {
      setAnswer(`Error: ${error.message}`);
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  };

  const startMeetingAudioCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true,
      });

      const audioTracks = stream.getAudioTracks();

      if (audioTracks.length === 0) {
        stream.getTracks().forEach((track) => track.stop());
        setAudioCaptureStatus(
          "No shared audio was detected. Please select a tab/window and enable audio sharing."
        );
        return;
      }

      const audioContext = new AudioContext();
      const audioSource = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();

      audioSource.connect(analyser);

      setAudioCaptureStatus(
        `Meeting audio capture is active. Audio tracks: ${audioTracks.length}`
      );

      window.meetMindAudioContext = audioContext;
      window.meetMindAudioAnalyser = analyser;

      setMeetingAudioStream(stream);

      stream.getVideoTracks().forEach((track) => {
        track.onended = () => {
          stream.getTracks().forEach((item) => item.stop());
          setMeetingAudioStream(null);
          setAudioCaptureStatus(
            "Meeting audio capture stopped."
          );
        };
      });
    } catch (error) {
      setAudioCaptureStatus(
        `Audio capture cancelled or failed: ${error.message}`
      );
    }
  };

  const stopMeetingAudioCapture = () => {
    if (meetingAudioStream) {
      meetingAudioStream.getTracks().forEach((track) => track.stop());
      setMeetingAudioStream(null);
    }

    setAudioCaptureStatus(
      "Meeting audio capture stopped."
    );
  };

  const testMeetingAudioRecording = () => {
    if (!meetingAudioStream) {
      setAudioRecordingStatus(
        "Connect meeting audio first."
      );
      return;
    }

    if (!window.MediaRecorder) {
      setAudioRecordingStatus(
        "Audio recording is not supported in this browser."
      );
      return;
    }

    const recorder = new MediaRecorder(
      meetingAudioStream
    );

    const chunks = [];

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    recorder.onstop = async () => {
      const audioBlob = new Blob(chunks, {
        type: recorder.mimeType || "audio/webm",
      });

      const audioUrl = URL.createObjectURL(audioBlob);

      setAudioDownloadUrl(audioUrl);

      const downloadLink = document.createElement("a");
      downloadLink.href = audioUrl;
      downloadLink.download = "meeting_audio_test.webm";
      downloadLink.textContent = "Download test audio";
      document.body.appendChild(downloadLink);

      setAudioRecordingStatus(
        `Audio recording captured successfully: ${Math.round(
          audioBlob.size / 1024
        )} KB. Transcribing...`
      );

      try {
        const data = await transcribeAudio(audioBlob);

        const transcribedText = data.text || "";

        setTranscript(
          transcribedText || "No speech detected."
        );

        setAudioRecordingStatus(
          `Transcription complete: ${
            transcribedText || "No speech detected."
          }`
        );

        setBackendOnline(true);

        if (transcribedText) {
          await processDetectedQuestion(transcribedText);
        }
      } catch (error) {
        setAudioRecordingStatus(
          `Transcription failed: ${error.message}`
        );
      }

      setTimeout(() => {
        downloadLink.remove();
        URL.revokeObjectURL(audioUrl);
      }, 30000);
    };

    recorder.start();

    setAudioRecordingStatus(
      "Recording meeting audio for 5 seconds..."
    );

    setTimeout(() => {
      if (recorder.state === "recording") {
        recorder.stop();
      }
    }, 5000);
  };

  const startAutoTranscription = () => {
    if (!meetingAudioStream) {
      setAudioRecordingStatus(
        "Connect meeting audio first."
      );
      return;
    }

    if (autoTranscribingRef.current) {
      return;
    }

    autoTranscribingRef.current = true;
    setIsAutoTranscribing(true);

    const recordChunk = () => {
      if (!meetingAudioStream || !autoTranscribingRef.current) {
        setIsAutoTranscribing(false);
        return;
      }

      const recorder = new MediaRecorder(
        meetingAudioStream
      );

      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, {
          type: recorder.mimeType || "audio/webm",
        });

        try {
          const data = await transcribeAudio(audioBlob);

          const transcribedText = data.text || "";

          if (transcribedText) {
            setTranscript((previous) =>
              previous
                ? `${previous} ${transcribedText}`
                : transcribedText
            );

            setDetectedQuestion(transcribedText);
          }

          setAudioRecordingStatus(
            transcribedText
              ? `Auto transcription: ${transcribedText}`
              : "No speech detected in this segment."
          );
        } catch (error) {
          setAudioRecordingStatus(
            `Auto transcription failed: ${error.message}`
          );
        }

        if (autoTranscribingRef.current) {
          recordChunk();
        }
      };

      recorder.start();

      setTimeout(() => {
        if (recorder.state === "recording") {
          recorder.stop();
        }
      }, 5000);
    };

    recordChunk();
  };

  const stopAutoTranscription = () => {
    autoTranscribingRef.current = false;
    setIsAutoTranscribing(false);
    setAudioRecordingStatus("Auto transcription stopped.");
  };

  const startLiveTranscript = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechError(
        "Live transcription is not supported in this browser."
      );
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setIsTranscribing(true);
      setSpeechError("");
    };

    recognition.onresult = (event) => {
      let combinedText = "";
      let latestFinalText = "";

      for (let i = 0; i < event.results.length; i++) {
        const text = event.results[i][0].transcript;

        combinedText += text + " ";

        if (event.results[i].isFinal) {
          latestFinalText = text.trim();
        }
      }

      setTranscript(combinedText.trim());

      if (latestFinalText) {
        processDetectedQuestion(latestFinalText);
      }
    };

    recognition.onerror = (event) => {
      setSpeechError(`Speech recognition error: ${event.error}`);
      setIsTranscribing(false);
    };

    recognition.onend = () => {
      setIsTranscribing(false);
    };

    recognition.start();

    window.meetMindRecognition = recognition;
  };

  const stopLiveTranscript = () => {
    if (window.meetMindRecognition) {
      window.meetMindRecognition.stop();
      window.meetMindRecognition = null;
    }

    setIsTranscribing(false);
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>MeetMind AI</h1>
          <p>AI Meeting Copilot</p>
        </div>

        <div className="status">
          <span
            className={`status-dot ${
              backendOnline ? "online" : "offline"
            }`}
          ></span>

          {backendOnline ? "Backend Online" : "Backend Offline"}
        </div>
      </header>

      <main className="main">
        <section className="hero">
          <h2>Your AI Meeting Companion</h2>
          <p>
            Ask questions and get concise AI-powered answers during your
            meetings.
          </p>
        </section>

        <section className="question-card">
          <label htmlFor="pdf-upload">
            Upload Meeting PDF
          </label>

          <input
            id="pdf-upload"
            type="file"
            accept=".pdf,application/pdf"
            onChange={(event) => {
              setPdfFile(event.target.files[0] || null);
              setPdfStatus("");
            }}
          />

          <button
            onClick={handlePDFUpload}
            disabled={!pdfFile || pdfUploading}
          >
            {pdfUploading
              ? "Uploading PDF..."
              : "Upload PDF"}
          </button>

          {pdfStatus && (
            <p className="pdf-status">
              {pdfStatus}
            </p>
          )}
        </section>

        <section className="question-card">
          <label>Live Meeting Transcript</label>

          <button
            onClick={startMeetingAudioCapture}
            disabled={!!meetingAudioStream}
          >
            {meetingAudioStream
              ? "Meeting Audio Connected"
              : "Connect Meeting Audio"}
          </button>

          <button
            className="clear-button"
            onClick={stopMeetingAudioCapture}
            disabled={!meetingAudioStream}
          >
            Stop Meeting Audio
          </button>

          <button
            className="clear-button"
            onClick={testMeetingAudioRecording}
            disabled={!meetingAudioStream}
          >
            Test Audio Recording
          </button>

          <button
            onClick={startAutoTranscription}
            disabled={!meetingAudioStream || isAutoTranscribing}
          >
            {isAutoTranscribing
              ? "Auto Transcription Active"
              : "Start Auto Transcription"}
          </button>

          <button
            className="clear-button"
            onClick={stopAutoTranscription}
            disabled={!isAutoTranscribing}
          >
            Stop Auto Transcription
          </button>

          {audioRecordingStatus && (
            <p className="pdf-status">
              {audioRecordingStatus}
            </p>
          )}

          {audioDownloadUrl && (
            <a
              href={audioDownloadUrl}
              download="meeting_audio_test.webm"
              className="clear-button"
              style={{ display: "block", textAlign: "center", textDecoration: "none" }}
            >
              Download Test Audio
            </a>
          )}

          {audioCaptureStatus && (
            <p className="pdf-status">
              {audioCaptureStatus}
            </p>
          )}

          <div className="transcript-status">
            <span
              className={`status-dot ${
                isTranscribing ? "online" : "offline"
              }`}
            ></span>

            {isTranscribing
              ? "Listening..."
              : "Transcription stopped"}
          </div>

          <div className="transcript-box">
            {transcript || "Your live transcript will appear here."}
          </div>

          <button
            onClick={startLiveTranscript}
            disabled={isTranscribing}
          >
            {isTranscribing ? "Listening..." : "Start Live Transcript"}
          </button>

          <button
            className="clear-button"
            onClick={stopLiveTranscript}
            disabled={!isTranscribing}
          >
            Stop Transcript
          </button>

          {speechError && (
            <p className="pdf-status">{speechError}</p>
          )}
        </section>

        {detectedQuestion && (
          <section className="question-card detected-question-card">
            <label>Detected Question</label>

            <div className="detected-question">
              {detectedQuestion}
            </div>
          </section>
        )}

        <section className="question-card">
          <label htmlFor="question">Ask MeetMind AI</label>

          <textarea
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Type your question here..."
            rows="5"
          />

          <button
            onClick={handleAskAI}
            disabled={!question.trim() || loading}
          >
            {loading ? "Thinking..." : "Ask AI"}
          </button>

          <button
            className="clear-button"
            onClick={handleClearConversation}
            type="button"
          >
            Clear Conversation
          </button>
        </section>

        {pdfUrl && answerSource === "pdf" && (
          <div className="pdf-viewer">
            <Document
              file={pdfUrl}
              loading="Loading PDF..."
              error="Failed to load PDF."
            >
              <div
                style={{
                  position: "relative",
                  width: "1000px",
                  maxWidth: "100%",
                }}
              >
                <Page
                  pageNumber={relevantBlock?.page || 1}
                  width={1000}
                />

                {relevantLine && (
                  <div
                    style={{
                      position: "absolute",
                      left: `${relevantLine.x0 * (1000 / 612)}px`,
                      top: `${relevantLine.y0 * (1000 / 612)}px`,
                      width: `${(relevantLine.x1 - relevantLine.x0) * (1000 / 612)}px`,
                      height: `${(relevantLine.y1 - relevantLine.y0) * (1000 / 612)}px`,
                      backgroundColor: "rgba(255, 255, 0, 0.55)",
                      borderRadius: "3px",
                      pointerEvents: "none",
                      zIndex: 10,
                    }}
                  />
                )}
              </div>
            </Document>
          </div>
        )}

        <section className="answer-card">
          <div className="card-title">
            <span>AI Answer</span>
            <span className="badge">
              {answerSource === "pdf" ? "PDF" : answerSource === "web" ? "Web" : "AI"}
            </span>
          </div>

          <div className="answer-placeholder">
            {answerSource === "web" && webResults.length > 0 ? (
              <div className="web-results">
                <div className="web-results-heading">
                  Web Search Results
                </div>

                {webResults.map((result, index) => (
                  <div className="web-result-card" key={`${result.url}-${index}`}>
                    <div className="web-result-number">
                      {index + 1}
                    </div>

                    <div className="web-result-content">
                      <h3>{result.title}</h3>

                      <p>{result.snippet}</p>

                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Open Source ?
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            ) : answer ? (
              <ReactMarkdown>{answer}</ReactMarkdown>
            ) : (
              "Your AI-generated answer will appear here."
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;