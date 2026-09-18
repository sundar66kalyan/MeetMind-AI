from faster_whisper import WhisperModel

MODEL_SIZE = "base.en"

_model = None


def get_model():
    global _model

    if _model is None:
        _model = WhisperModel(
            MODEL_SIZE,
            device="cpu",
            compute_type="int8"
        )

    return _model


def transcribe_audio(file_path: str) -> dict:
    model = get_model()

    segments, info = model.transcribe(
        file_path,
        beam_size=5,
        vad_filter=False,
        initial_prompt=(
            "Technical meeting discussion about AI, machine learning, "
            "RAG, retrieval augmented generation, LLMs, LangChain, "
            "embeddings, vector databases, APIs, NLP, GenAI, "
            "Python, FastAPI, Streamlit, machine learning models."
        )
    )

    segment_list = list(segments)

    text = " ".join(
        segment.text.strip()
        for segment in segment_list
        if segment.text.strip()
    ).strip()

    return {
        "text": text,
        "language": info.language,
        "language_probability": info.language_probability,
        "segments": [
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            }
            for segment in segment_list
        ]
    }