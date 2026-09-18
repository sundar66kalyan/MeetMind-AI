from pathlib import Path
import re

import chromadb


VECTOR_DB_PATH = Path("data") / "chroma_db"

client = chromadb.PersistentClient(
    path=str(VECTOR_DB_PATH)
)

collection = client.get_or_create_collection(
    name="meeting_documents"
)

interview_collection = client.get_or_create_collection(
    name="interview_questions"
)


def add_documents(
    chunks: list[dict],
    document_id: str = "default-document",
    filename: str = "",
    document_type: str = "resume"
) -> None:
    """
    Store document chunks in ChromaDB.

    Each chunk receives a document-specific ID so that
    multiple PDFs can be stored without overwriting
    each other.
    """

    if not chunks:
        return

    ids = []
    documents = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        chunk_id = f"{document_id}-chunk-{index}"

        ids.append(chunk_id)
        documents.append(chunk["text"])

        metadatas.append(
            {
                "page": chunk["page"],
                "document_id": document_id,
                "filename": filename,
                "document_type": document_type
            }
        )

    target_collection = (
        interview_collection
        if document_type == "interview_questions"
        else collection
    )

    target_collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )


def search_documents(
    question: str,
    top_k: int = 5
) -> dict:
    """
    Search meeting documents using semantic similarity.
    """

    if collection.count() == 0:
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

    candidate_count = min(
        max(top_k * 5, 20),
        collection.count()
    )

    results = collection.query(
        query_texts=[question],
        n_results=candidate_count
    )

    return results


def search_interview_questions(
    question: str,
    top_k: int = 5
) -> dict:
    """
    Search only the interview-question PDF collection.
    """

    if interview_collection.count() == 0:
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

    candidate_count = min(
        max(top_k * 5, 20),
        interview_collection.count()
    )

    results = interview_collection.query(
        query_texts=[question],
        n_results=candidate_count
    )

    return results


def find_relevant_interview_question(
    question: str,
    top_k: int = 5,
    relevance_threshold: float = 1.70
) -> dict | None:
    """
    Find the most relevant interview question/answer
    from the interview-question collection.
    """

    results = search_interview_questions(
        question=question,
        top_k=top_k
    )

    if not results["documents"] or not results["documents"][0]:
        return None

    best_index = 0

    best_distance = results["distances"][0][0]

    for index, distance in enumerate(results["distances"][0]):
        if distance < best_distance:
            best_distance = distance
            best_index = index

    if best_distance > relevance_threshold:
        return None

    return {
        "text": results["documents"][0][best_index],
        "page": results["metadatas"][0][best_index].get("page"),
        "filename": results["metadatas"][0][best_index].get(
            "filename",
            ""
        ),
        "document_type": results["metadatas"][0][best_index].get(
            "document_type",
            ""
        ),
        "distance": best_distance
    }


def is_interview_question(question: str) -> bool:
    """
    Detect whether a question is likely an interview
    technical/concept question.
    """

    question_lower = question.lower().strip()

    interview_patterns = [
        "what is ",
        "what are ",
        "what was ",
        "what were ",
        "who is ",
        "why use ",
        "why do ",
        "why does ",
        "why is ",
        "why are ",
        "how does ",
        "how do ",
        "how is ",
        "how are ",
        "explain ",
        "can you explain ",
        "could you explain ",
        "define ",
        "difference between ",
        "difference among ",
        "compare ",
        "advantages of ",
        "disadvantages of ",
        "benefits of ",
        "use cases of ",
    ]

    return any(
        question_lower.startswith(pattern)
        for pattern in interview_patterns
    )


def get_collection_count() -> int:
    """
    Return the number of stored document chunks.
    """

    return collection.count()


def _keyword_score(
    question: str,
    document: str
) -> int:
    """
    Calculate keyword relevance between the question
    and document text.

    Exact multi-word phrases receive a strong bonus.
    """
    
    question_normalized = " ".join(
        question.lower().split()
    )

    document_normalized = " ".join(
        document.lower().split()
    )

    score = 0

    # Strong bonus for exact phrases.
    important_phrases = [
        phrase
        for phrase in [
            "technical skills",
            "professional summary",
            "key achievements",
            "featured projects",
            "education",
            "certifications",
            "work experience",
            "ai product intelligence suite",
            "intelligent rag-based chatbot",
        ]
        if phrase in question_normalized
    ]

    for phrase in important_phrases:
        if phrase in document_normalized:
            score += 10

    # Normal keyword overlap.
    question_words = {
        word.lower()
        for word in re.findall(
            r"[A-Za-z0-9]+",
            question
        )
        if len(word) >= 3
    }

    document_words = {
        word.lower()
        for word in re.findall(
            r"[A-Za-z0-9]+",
            document
        )
        if len(word) >= 3
    }

    score += len(
        question_words.intersection(document_words)
    )

    return score


def search_relevant_documents(
    question: str,
    top_k: int = 5
) -> list[dict]:
    """
    Return document search results using a combination of
    semantic similarity and keyword matching.
    """

    results = search_documents(
        question=question,
        top_k=top_k
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    formatted_results = []

    for index, document in enumerate(results["documents"][0]):
        distance = results["distances"][0][index]
        keyword_score = _keyword_score(
            question=question,
            document=document
        )

        metadata = results["metadatas"][0][index]

        filename = metadata.get("filename", "").strip()

        # Ignore legacy chunks created before filename metadata
        # was added to the vector database.
        if not filename:
            continue

        formatted_results.append(
            {
                "text": document,
                "page": metadata["page"],
                "distance": distance,
                "keyword_score": keyword_score,
                "document_id": metadata.get(
                    "document_id",
                    ""
                ),
                "filename": filename,
            }
        )

    # Prefer strong keyword matches first.
    # Semantic distance is used as the secondary signal.
    formatted_results.sort(
        key=lambda item: (
            -item["keyword_score"],
            item["distance"]
        )
    )

    # For exact project-name questions, prefer the chunk
    # with the better semantic match when keyword scores
    # are inflated by a large page-level chunk.
    if "ai product intelligence suite" in question.lower():
        formatted_results.sort(
            key=lambda item: item["distance"]
        )

    return formatted_results[:top_k]


def find_relevant_document(
    question: str,
    top_k: int = 5,
    relevance_threshold: float = 1.70
) -> dict | None:
    """
    Find the most relevant PDF chunk for a question.

    Uses both keyword overlap and ChromaDB semantic distance.
    """

    results = search_relevant_documents(
        question=question,
        top_k=top_k
    )

    if not results:
        return None

    best_match = max(
        results,
        key=lambda item: (
            item["keyword_score"],
            -item["distance"]
        )
    )

    # Allow strong exact keyword matches even when
    # semantic distance is slightly higher.
    if (
        best_match["distance"] <= relevance_threshold
        or best_match["keyword_score"] >= 2
    ):
        return best_match

    return None