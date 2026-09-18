import re
import time

from google import genai

from backend.app.core.config import settings
from backend.app.models.session import ChatMessage


client = genai.Client(api_key=settings.GOOGLE_API_KEY)


def generate_answer(
    question: str,
    history: list[ChatMessage] | None = None
) -> str:

    history = history or []

    conversation = []

    for message in history:
        conversation.append(
            f"{message.role.upper()}: {message.content}"
        )

    conversation.append(
        f"USER: {question}"
    )

    prompt = (
        "You are MeetMind AI, an AI meeting assistant.\n\n"
        "Use the conversation history to understand references such as "
        "'it', 'its', 'they', 'this', and 'that'. "
        "When the latest question contains an ambiguous reference, "
        "resolve it using the most recent relevant topic in the conversation. "
        "Do not invent a new topic when the conversation already provides context.\n\n"
        "Give concise, accurate answers suitable for professional "
        "meeting discussions and interview preparation.\n\n"
        "CONVERSATION HISTORY:\n"
        + "\n".join(conversation)
        + "\n\n"
        "Answer the latest USER question using the conversation history."
    )

    last_error = None

    for attempt in range(3):

        try:
            response = client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )

            return response.text.strip()

        except Exception as e:
            last_error = e

            if attempt < 2:
                time.sleep(3)

    raise last_error

def generate_pdf_answer(
    question: str,
    document_text: str,
    page: int
) -> str:
    """
    Generate an answer using retrieved PDF content.
    """

    prompt = (
        "You are MeetMind AI, an AI meeting assistant.\n\n"
        "Answer the user's question using ONLY the provided PDF content.\n"
        "Do not add information that is not supported by the PDF.\n"
        "If the PDF content does not clearly answer the question, say so.\n"
        "Keep the answer concise and professional.\n\n"
        f"PDF PAGE: {page}\n\n"
        "PDF CONTENT:\n"
        f"{document_text}\n\n"
        f"USER QUESTION:\n{question}\n\n"
        "Provide the answer and mention the PDF page number."
    )

    last_error = None

    for attempt in range(3):

        try:
            response = client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )

            return response.text.strip()

        except Exception as e:
            last_error = e

            if attempt < 2:
                time.sleep(3)

    raise last_error

def answer_from_pdf(
    question: str,
    top_k: int = 5
) -> dict:
    """
    Search the PDF knowledge base and generate an answer
    when a relevant document is found.
    """

    from backend.app.services.vector_service import (
        find_relevant_document
    )

    document = find_relevant_document(
        question=question,
        top_k=top_k
    )

    if document is None:
        return {
            "source": "none",
            "answer": None,
            "page": None,
            "distance": None,
        }

    answer = generate_pdf_answer(
        question=question,
        document_text=document["text"],
        page=document["page"]
    )

    return {
        "source": "pdf",
        "answer": answer,
        "page": document["page"],
        "distance": document["distance"],
    }

def build_pdf_answer(
    question: str,
    top_k: int = 5
) -> dict:
    """
    Retrieve relevant PDF content and return a useful
    answer based on the matched PDF section.
    """

    from backend.app.services.vector_service import (
        find_relevant_document
    )

    document = find_relevant_document(
        question=question,
        top_k=top_k
    )

    if document is None:
        return {
            "source": "none",
            "answer": None,
            "page": None,
            "distance": None,
            "matched_text": None,
            "filename": "",
            "document_id": "",
        }

    text = document["text"].strip()

    # For section-based questions, return the complete
    # relevant section instead of only the heading.
    section_headers = [
        "TECHNICAL SKILLS",
        "PROFESSIONAL SUMMARY",
        "KEY ACHIEVEMENTS",
        "FEATURED PROJECTS",
        "EDUCATION",
        "CERTIFICATIONS",
        "WORK EXPERIENCE",
    ]

    question_lower = question.lower()

    print("DEBUG question_lower:", question_lower)
    print(
        "DEBUG project title match:",
        "ai product intelligence suite" in question_lower
    )
    print(
        "DEBUG title in retrieved text:",
        "ai product intelligence suite" in text.lower()
    )

    if (
        "technical skills" in question_lower
        and "TECHNICAL SKILLS" in text
    ):
        start = text.find("TECHNICAL SKILLS")
        section_text = text[start:]

        next_headers = [
            header
            for header in section_headers
            if header != "TECHNICAL SKILLS"
            and header in section_text
        ]

        if next_headers:
            end_positions = [
                section_text.find(header)
                for header in next_headers
                if section_text.find(header) > 0
            ]

            if end_positions:
                section_text = section_text[:min(end_positions)]

        text = section_text.strip()

    if (
        "professional summary" in question_lower
        and "PROFESSIONAL SUMMARY" in text
    ):
        start = text.find("PROFESSIONAL SUMMARY")
        section_text = text[start:]

        next_headers = [
            "KEY ACHIEVEMENTS",
            "TECHNICAL SKILLS",
            "FEATURED PROJECTS",
            "EDUCATION",
            "CERTIFICATIONS",
            "WORK EXPERIENCE",
        ]

        end_positions = [
            section_text.find(header)
            for header in next_headers
            if section_text.find(header) > 0
        ]

        if end_positions:
            section_text = section_text[:min(end_positions)]

        text = section_text.strip()

    if (
        "key achievements" in question_lower
        and "KEY ACHIEVEMENTS" in text
    ):
        start = text.find("KEY ACHIEVEMENTS")
        section_text = text[start:]

        next_headers = [
            "TECHNICAL SKILLS",
            "FEATURED PROJECTS",
            "EDUCATION",
            "CERTIFICATIONS",
            "WORK EXPERIENCE",
        ]

        end_positions = [
            section_text.find(header)
            for header in next_headers
            if section_text.find(header) > 0
        ]

        if end_positions:
            section_text = section_text[:min(end_positions)]

        text = section_text.strip()

    # ---------------------------------------------------------
    # PROJECT-SPECIFIC QUESTIONS
    # ---------------------------------------------------------

    project_names = [
        "AI Product Intelligence Suite",
        "Intelligent RAG-Based Chatbot",
        "AI Financial Copilot",
        "Traffic Sign Recognition & Detection",
        "Multi-Agent AI Business Assistant",
        "AI Dynamic Pricing Engine",
        "Skin Disorder Type Detection",
        "Multi-Class Object Detection",
        "Customer Transaction Prediction",
        "Rice Leaf Disease Detection",
        "Telecom Customer Churn Prediction",
        "Pneumonia Detection, Chest X-Rays",
        "Employee Performance Prediction",
        "Indian Sign Language Recognition",
        "Home Loan Eligibility Prediction",
    ]

    if (
        "project" in question_lower
        or any(
            project_name.lower() in question_lower
            for project_name in project_names
        )
    ):
        matched_project = None

        for project_name in project_names:
            if project_name.lower() in question_lower:
                matched_project = project_name
                break

        if matched_project:
            start = text.lower().find(
                matched_project.lower()
            )

            if start >= 0:
                project_text = text[start:]

                # Find the next project heading.
                # PDF extraction may truncate the project title,
                # so also stop at numbered project headings.

                remaining_text = project_text[
                    len(matched_project):
                ]

                next_project_positions = []

                # 1. Look for complete known project names
                for project_name in project_names:
                    if (
                        project_name.lower()
                        == matched_project.lower()
                    ):
                        continue

                    position = remaining_text.lower().find(
                        project_name.lower()
                    )

                    if position >= 0:
                        next_project_positions.append(position)

                # 2. Look for the next numbered project heading
                #    such as "2. Intellig", "3. AI Financial", etc.
                numbered_project_match = re.search(
                    r"\n\s*\d+\.\s+",
                    remaining_text
                )

                if numbered_project_match:
                    next_project_positions.append(
                        numbered_project_match.start()
                    )

                if next_project_positions:
                    end_position = min(
                        next_project_positions
                    )

                    project_text = (
                        project_text[
                            :len(matched_project)
                            + end_position
                        ]
                    )

                text = project_text.strip()

    answer = (
        f"{text}\n\n"
        f"Source: PDF, Page {document['page']}"
    )

    return {
        "source": "pdf",
        "answer": answer,
        "page": document["page"],
        "distance": document["distance"],
        "matched_text": document["text"],
        "filename": document.get("filename", ""),
        "document_id": document.get("document_id", ""),
    }