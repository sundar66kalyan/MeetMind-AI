import pymupdf


def extract_pdf_text(file_path: str) -> list[dict]:
    pages = []

    document = pymupdf.open(file_path)

    try:
        for page_number, page in enumerate(
            document,
            start=1
        ):
            text = page.get_text("text").strip()

            if text:
                pages.append(
                    {
                        "page": page_number,
                        "text": text
                    }
                )
    finally:
        document.close()

    return pages


def chunk_document_pages(
    pages: list[dict],
    chunk_size: int = 2000,
    chunk_overlap: int = 200
) -> list[dict]:
    chunks = []

    for page in pages:
        text = page["text"]
        page_number = page["page"]

        start = 0

        while start < len(text):
            end = start + chunk_size

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    {
                        "page": page_number,
                        "text": chunk_text
                    }
                )

            if end >= len(text):
                break

            start = end - chunk_overlap

    return chunks


def find_pdf_highlights(
    file_path: str,
    page_number: int,
    question: str
) -> list[dict]:
    import re

    document = pymupdf.open(file_path)

    try:
        if page_number < 1 or page_number > len(document):
            return []

        page = document[page_number - 1]

        stop_words = {
            "what",
            "is",
            "are",
            "was",
            "were",
            "the",
            "a",
            "an",
            "of",
            "to",
            "in",
            "on",
            "for",
            "and",
            "or",
            "how",
            "why",
            "when",
            "where",
            "can",
            "could",
            "does",
            "do",
            "about",
            "tell",
            "me",
            "please",
        }

        words = re.findall(
            r"[A-Za-z0-9]+",
            question.lower()
        )

        terms = [
            word
            for word in words
            if len(word) >= 3
            and word not in stop_words
        ]

        highlights = []

        for term in terms:
            rectangles = page.search_for(term)

            for rectangle in rectangles:
                highlights.append(
                    {
                        "page": page_number,
                        "x0": rectangle.x0,
                        "y0": rectangle.y0,
                        "x1": rectangle.x1,
                        "y1": rectangle.y1,
                        "text": term,
                    }
                )

        return highlights

    finally:
        document.close()


def find_relevant_block(
    file_path: str,
    page_number: int,
    question: str
) -> dict | None:
    import re

    document = pymupdf.open(file_path)

    try:
        if page_number < 1 or page_number > len(document):
            return None

        page = document[page_number - 1]
        blocks = page.get_text("blocks")

        matched_words = {
            word.lower()
            for word in re.findall(
                r"[A-Za-z0-9]+",
                question
            )
            if len(word) >= 3
        }

        stop_words = {
            "the",
            "and",
            "that",
            "this",
            "with",
            "from",
            "page",
            "content",
            "information",
            "provides",
            "using",
        }

        matched_words -= stop_words

        best_block = None
        best_score = 0

        for block in blocks:
            block_text = block[4].strip()

            if not block_text:
                continue

            block_words = {
                word.lower()
                for word in re.findall(
                    r"[A-Za-z0-9]+",
                    block_text
                )
                if len(word) >= 3
            }

            score = len(
                matched_words.intersection(
                    block_words
                )
            )

            if score > best_score:
                best_score = score
                best_block = block

        if best_block is None or best_score == 0:
            return None

        return {
            "page": page_number,
            "x0": best_block[0],
            "y0": best_block[1],
            "x1": best_block[2],
            "y1": best_block[3],
            "text": best_block[4].strip(),
            "score": best_score,
        }

    finally:
        document.close()


def find_relevant_line(
    file_path: str,
    page_number: int,
    question: str
) -> dict | None:
    import re

    document = pymupdf.open(file_path)

    try:
        if page_number < 1 or page_number > len(document):
            return None

        page = document[page_number - 1]

        question_words = {
            word.lower()
            for word in re.findall(
                r"[A-Za-z0-9]+",
                question
            )
            if len(word) >= 3
        }

        stop_words = {
            "what",
            "who",
            "when",
            "where",
            "which",
            "why",
            "how",
            "does",
            "the",
            "are",
            "is",
            "can",
            "you",
            "explain",
            "tell",
            "about",
        }

        question_words -= stop_words

        words = page.get_text("words")

        if not words:
            return None

        lines = {}

        for word in words:
            x0, y0, x1, y1, text = word[:5]
            block_no = word[5]
            line_no = word[6]

            key = (block_no, line_no)

            if key not in lines:
                lines[key] = {
                    "words": [],
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                }

            lines[key]["words"].append(text)

            lines[key]["x0"] = min(
                lines[key]["x0"],
                x0
            )

            lines[key]["y0"] = min(
                lines[key]["y0"],
                y0
            )

            lines[key]["x1"] = max(
                lines[key]["x1"],
                x1
            )

            lines[key]["y1"] = max(
                lines[key]["y1"],
                y1
            )

        best_line = None
        best_score = 0

        for line in lines.values():
            line_text = " ".join(
                line["words"]
            )

            line_words = {
                word.lower()
                for word in re.findall(
                    r"[A-Za-z0-9]+",
                    line_text
                )
            }

            score = len(
                question_words.intersection(
                    line_words
                )
            )

            if score > best_score:
                best_score = score
                best_line = line

        if best_line is None or best_score == 0:
            return None

        return {
            "page": page_number,
            "x0": best_line["x0"],
            "y0": best_line["y0"],
            "x1": best_line["x1"],
            "y1": best_line["y1"],
            "text": " ".join(
                best_line["words"]
            ),
            "score": best_score,
        }

    finally:
        document.close()


def find_interview_answer(
    file_path: str,
    page_number: int,
    question: str
) -> dict | None:
    """
    Find the exact interview question in the PDF and return
    its answer, including answers that continue onto the next page.
    """

    import re

    document = pymupdf.open(file_path)

    try:
        if page_number < 1 or page_number > len(document):
            return None

        # Search the retrieved page and the next page.
        search_pages = [page_number]

        if page_number < len(document):
            search_pages.append(page_number + 1)

        normalized_question = re.sub(
            r"[^a-z0-9\s]",
            "",
            question.lower()
        ).strip()

        normalized_question = re.sub(
            r"^(can you|could you|please|tell me)\s+",
            "",
            normalized_question
        ).strip()

        best_match = None

        # ---------------------------------------------------------
        # FIND EXACT QUESTION
        # ---------------------------------------------------------

        for current_page_number in search_pages:

            page = document[current_page_number - 1]

            lines = [
                line.strip()
                for line in page.get_text("text").splitlines()
                if line.strip()
            ]

            for index, line in enumerate(lines):

                # Check numbered question and allow PDF line wrapping.
                if not re.match(r"^\d+\.\s+", line):
                    continue

                # Ignore known numbered section headings.
                if re.match(
                    r"^(11|12|13|14|15)\.\s+",
                    line
                ):
                    continue

                question_candidate = line

                # If this line already ends the question,
                # do not combine the Answer text with it.
                if not (
                    line.endswith("?")
                    or line.endswith(".")
                ):
                    # Combine wrapped question lines.
                    for next_index in range(index + 1, len(lines)):
                        next_line = lines[next_index]

                        if re.match(r"^\d+\.\s+", next_line):
                            break

                        question_candidate += " " + next_line

                        if next_line.endswith("?") or next_line.endswith("."):
                            break

                normalized_line = re.sub(
                    r"^\d+\.\s+",
                    "",
                    question_candidate.lower()
                )

                normalized_line = re.sub(
                    r"[^a-z0-9\s]",
                    "",
                    normalized_line
                ).strip()

                print(
                    "DEBUG candidate:",
                    repr(question_candidate),
                    "=>",
                    repr(normalized_line)
                )

                # Exact match gets priority.
                if normalized_question == normalized_line:
                    best_match = {
                        "page": current_page_number,
                        "index": index,
                        "lines": lines,
                        "question": question_candidate,
                    }
                    break

            if best_match:
                break

        if not best_match:
            print("DEBUG best_match:", best_match)
            return None

        matched_page = best_match["page"]
        matched_index = best_match["index"]
        matched_question = best_match["question"]
        current_lines = best_match["lines"]

        # ---------------------------------------------------------
        # COLLECT ANSWER
        # ---------------------------------------------------------

        answer_lines = []
        answer_started = False

        # First collect everything after the question on the same page.
        for line in current_lines[matched_index + 1:]:

            # If another interview question starts, stop.
            if re.match(
                r"^\d+\.\s+.*[?.]$",
                line
            ):
                break

            if line.lower() in {
                "answer:",
                "answer"
            }:
                answer_started = True
                continue

            if answer_started:
                answer_lines.append(line)

        # ---------------------------------------------------------
        # ANSWER CONTINUES ON NEXT PAGE
        # ---------------------------------------------------------

        if matched_page < len(document) and not answer_lines:

            next_page = document[matched_page]

            next_lines = [
                line.strip()
                for line in next_page.get_text("text").splitlines()
                if line.strip()
            ]

            # Check whether the next page begins with Answer:
            next_answer_started = False

            for line in next_lines:

                if line.lower() in {
                    "answer:",
                    "answer"
                }:
                    next_answer_started = True
                    continue

                # Stop when a new interview question starts.
                if re.match(
                    r"^\d+\.\s+.*[?.]$",
                    line
                ):
                    break

                # Ignore numbered section headings.
                if re.match(
                    r"^\d+\.\s+[^?]+$",
                    line
                ):
                    continue

                if next_answer_started:
                    answer_lines.append(line)

        # ---------------------------------------------------------
        # CLEAN ANSWER
        # ---------------------------------------------------------

        answer_text = " ".join(answer_lines).strip()

        if not answer_text:
            return None

        print(
            "DEBUG exact interview question:",
            matched_question
        )

        print(
            "DEBUG interview answer:",
            answer_text
        )

        return {
            "page": matched_page,
            "question": matched_question,
            "answer": answer_text,
            "score": 100,
        }

    finally:
        document.close()