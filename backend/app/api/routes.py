from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from backend.app.services.upload_service import process_uploaded_pdf

from backend.app.services.document_service import (
    find_pdf_highlights,
    find_relevant_block,
    find_relevant_line,
    find_interview_answer,
)

from backend.app.models.schemas import (
    QuestionRequest,
    AnswerResponse,
)

from backend.app.services.llm_service import generate_answer

from backend.app.services.vector_service import (
    is_interview_question,
    find_relevant_interview_question,
)

from backend.app.services.session_service import (
    get_messages,
    add_message,
    clear_session,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api",
    tags=["AI"],
)


# =========================================================
# FOLLOW-UP QUESTION RESOLUTION
# =========================================================

def resolve_follow_up_question(
    question: str,
    history
) -> str:

    if not history:
        return question

    follow_up_phrases = [
        "what does it do",
        "what does it do?",
        "how does it work",
        "how does it work?",
        "why is it useful",
        "why is it useful?",
        "what are its benefits",
        "what are its benefits?",
        "explain it",
        "explain it?",
        "tell me more about it",
        "tell me more about it?",
        "what about it",
        "what about it?",
    ]

    normalized_question = question.lower().strip()

    is_follow_up = any(
        phrase in normalized_question
        for phrase in follow_up_phrases
    )

    if not is_follow_up:
        return question

    previous_user_questions = [
        message.content
        for message in history
        if message.role == "user"
    ]

    if not previous_user_questions:
        return question

    previous_question = previous_user_questions[-1]

    return (
        f"Regarding the topic from the previous question "
        f"('{previous_question}'), {question}"
    )


# =========================================================
# API STATUS
# =========================================================

@router.get("/status")
def api_status():

    return {
        "status": "online",
        "service": "MeetMind AI API",
        "provider": "google",
        "model": "gemini-3.6-flash",
    }


# =========================================================
# SERVE UPLOADED PDF
# =========================================================

@router.get("/pdf/{filename}")
def get_pdf(filename: str):

    from pathlib import Path

    documents_dir = Path("data") / "documents"

    safe_filename = Path(filename).name

    file_path = documents_dir / safe_filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file not found.",
        )

    if file_path.suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=safe_filename,
    )


# =========================================================
# ASK QUESTION
# =========================================================

@router.post("/ask")
def ask_question(request: QuestionRequest):

    question = request.question.strip()

    session_id = request.session_id.strip()

    if not session_id:
        session_id = "default"

    if not question:
        return {
            "question": "",
            "answer": "Please provide a question.",
            "session_id": session_id,
            "source": "none",
            "page": None,
            "distance": None,
            "results": [],
            "status": "empty_question",
        }

    try:

        from pathlib import Path

        from backend.app.services.llm_service import (
            build_pdf_answer,
        )

        from backend.app.services.web_search_service import (
            build_web_answer,
        )

        # -------------------------------------------------
        # Resolve follow-up questions
        # -------------------------------------------------

        history = get_messages(session_id)

        resolved_question = resolve_follow_up_question(
            question=question,
            history=history,
        )

        # -------------------------------------------------
        # Step 1: Interview-question knowledge base
        # -------------------------------------------------

        if is_interview_question(resolved_question):

            interview_result = find_relevant_interview_question(
                question=resolved_question,
            )

            if interview_result:
                pass

        # -------------------------------------------------
        # Step 2: Search uploaded PDF
        # -------------------------------------------------

        pdf_result = build_pdf_answer(
            question=resolved_question,
        )

        # -------------------------------------------------
        # PDF is relevant
        # -------------------------------------------------

        if pdf_result["source"] == "pdf":

            pdf_filename = (
                pdf_result.get("filename", "").strip()
            )

            if not pdf_filename:
                raise HTTPException(
                    status_code=500,
                    detail="Retrieved PDF filename is missing.",
                )

            # -------------------------------------------------
            # Exact interview Q&A extraction
            # -------------------------------------------------

            interview_answer = None

            print(
                "DEBUG is_interview_question:",
                is_interview_question(resolved_question),
            )

            if is_interview_question(resolved_question):

                interview_answer = find_interview_answer(
                    file_path=str(
                        Path("data")
                        / "documents"
                        / pdf_filename
                    ),
                    page_number=pdf_result["page"],
                    question=resolved_question,
                )

            # -------------------------------------------------
            # PDF path
            # -------------------------------------------------

            pdf_path = (
                Path("data")
                / "documents"
                / pdf_filename
            )

            # -------------------------------------------------
            # Relevant line
            # -------------------------------------------------

            relevant_line = find_relevant_line(
                file_path=str(pdf_path),
                page_number=pdf_result["page"],
                question=resolved_question,
            )

            # -------------------------------------------------
            # Relevant block
            # -------------------------------------------------

            relevant_block = find_relevant_block(
                file_path=str(pdf_path),
                page_number=pdf_result["page"],
                question=resolved_question,
            )

            # -------------------------------------------------
            # Answer selection
            # -------------------------------------------------

            if interview_answer:

                answer = (
                    f"{interview_answer['question']}\n\n"
                    f"Answer:\n"
                    f"{interview_answer['answer']}\n\n"
                    f"Source: PDF, "
                    f"Page {interview_answer['page']}"
                )

            elif relevant_line:

                question_lower = (
                    resolved_question.lower()
                )

                # -------------------------------------------------
                # Project detection
                # -------------------------------------------------

                is_project_question = (
                    "project" in question_lower
                    or "ai product intelligence suite"
                    in question_lower
                    or "intelligent rag-based chatbot"
                    in question_lower
                    or "ai financial copilot"
                    in question_lower
                    or "traffic sign recognition"
                    in question_lower
                    or "multi-agent ai business assistant"
                    in question_lower
                    or "ai dynamic pricing engine"
                    in question_lower
                    or "skin disorder type detection"
                    in question_lower
                    or "multi-class object detection"
                    in question_lower
                    or "customer transaction prediction"
                    in question_lower
                    or "rice leaf disease detection"
                    in question_lower
                    or "telecom customer churn prediction"
                    in question_lower
                    or "pneumonia detection"
                    in question_lower
                    or "employee performance prediction"
                    in question_lower
                    or "indian sign language recognition"
                    in question_lower
                    or "home loan eligibility prediction"
                    in question_lower
                )

                # -------------------------------------------------
                # Section/project questions
                # -------------------------------------------------

                if (
                    "technical skills" in question_lower
                    or "professional summary"
                    in question_lower
                    or "key achievements"
                    in question_lower
                    or "featured projects"
                    in question_lower
                    or is_project_question
                    or "education" in question_lower
                    or "certifications" in question_lower
                    or "work experience" in question_lower
                ):

                    answer = pdf_result["answer"]

                elif (
                    resolved_question != question
                    and relevant_block
                ):

                    answer = (
                        f"{relevant_block['text']}\n\n"
                        f"Source: PDF, "
                        f"Page {relevant_block['page']}"
                    )

                else:

                    answer = (
                        f"{relevant_line['text']}\n\n"
                        f"Source: PDF, "
                        f"Page {relevant_line['page']}"
                    )

            else:

                answer = pdf_result["answer"]

            # -------------------------------------------------
            # PDF highlights
            # -------------------------------------------------

            highlights = find_pdf_highlights(
                file_path=str(pdf_path),
                page_number=pdf_result["page"],
                question=resolved_question,
            )

            # -------------------------------------------------
            # Save user message
            # -------------------------------------------------

            add_message(
                session_id=session_id,
                role="user",
                content=question,
            )

            # -------------------------------------------------
            # Save assistant response
            # -------------------------------------------------

            add_message(
                session_id=session_id,
                role="assistant",
                content=answer,
            )

            # -------------------------------------------------
            # Return PDF response
            # -------------------------------------------------

            return {
                "question": question,
                "answer": answer,
                "session_id": session_id,
                "source": "pdf",
                "page": pdf_result["page"],
                "distance": pdf_result["distance"],
                "matched_text": pdf_result["matched_text"],
                "highlights": highlights,
                "relevant_block": relevant_block,
                "relevant_line": relevant_line,
                "results": [],
                "status": "answered_from_pdf",
            }

        # -----------------------------------------------------
        # Step 3: PDF not relevant → Web search
        # -----------------------------------------------------

        web_result = build_web_answer(
            question=resolved_question,
        )

        answer = web_result["answer"]

        # -------------------------------------------------
        # Save user message
        # -------------------------------------------------

        add_message(
            session_id=session_id,
            role="user",
            content=question,
        )

        # -------------------------------------------------
        # Save assistant response
        # -------------------------------------------------

        add_message(
            session_id=session_id,
            role="assistant",
            content=answer or "",
        )

        # -------------------------------------------------
        # Return web response
        # -------------------------------------------------

        return {
            "question": question,
            "answer": answer,
            "session_id": session_id,
            "source": "web",
            "page": None,
            "distance": None,
            "results": web_result["results"],
            "status": "answered_from_web",
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# SESSION HISTORY
# =========================================================

@router.get("/sessions/{session_id}")
def get_session_history(session_id: str):

    messages = get_messages(session_id)

    return {
        "session_id": session_id,
        "messages": messages,
    }


# =========================================================
# DELETE SESSION
# =========================================================

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):

    clear_session(session_id)

    return {
        "session_id": session_id,
        "status": "cleared",
    }


# =========================================================
# UPLOAD PDF
# =========================================================

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    document_type: str = Form("resume"),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was selected.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    from pathlib import Path

    documents_dir = Path("data") / "documents"

    documents_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = documents_dir / file.filename

    try:

        contents = await file.read()

        with open(file_path, "wb") as output_file:
            output_file.write(contents)

        result = process_uploaded_pdf(
            file_path=str(file_path),
            document_type=document_type,
        )

        result["pdf_url"] = (
            f"/api/pdf/{file_path.name}"
        )

        return result

    except Exception as e:

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# AUDIO TRANSCRIPTION
# =========================================================

@router.post("/transcribe-audio")
async def transcribe_audio(
    file: UploadFile = File(...),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No audio file was selected.",
        )

    allowed_extensions = {
        ".webm",
        ".wav",
        ".mp3",
        ".m4a",
    }

    from pathlib import Path

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio format.",
        )

    audio_dir = Path("data") / "audio"

    audio_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        audio_dir
        / f"meeting_audio{extension}"
    )

    try:

        contents = await file.read()

        with open(file_path, "wb") as output_file:
            output_file.write(contents)

        from backend.app.services.transcription_service import (
            transcribe_audio,
        )

        result = transcribe_audio(
            file_path=str(file_path),
        )

        return {
            "text": result["text"],
            "language": result["language"],
            "language_probability": result[
                "language_probability"
            ],
            "segments": result["segments"],
            "status": "transcribed",
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    finally:

        if file_path.exists():
            file_path.unlink()