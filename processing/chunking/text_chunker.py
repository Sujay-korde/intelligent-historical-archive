import re
from typing import List
from processing.base import ExtractedContent
from processing.chunking.base import ChunkDTO, Chunker


class TextChunker(Chunker):
    """
    Paragraph- and page-aware chunker.
    Preserves page boundaries where possible, groups paragraphs, and breaks
    at sentence boundaries with overlap when text exceeds max_tokens.
    """
    strategy_name: str = "TextChunker"

    def _estimate_tokens(self, text: str) -> int:
        # Fast whitespace-based token estimation (approx 1.3 words per token or ~4 chars per token)
        return max(1, len(text.split()))

    def _split_into_sentences(self, text: str) -> List[str]:
        # Regex to split text into sentences
        sentence_end = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_end.split(text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def chunk(
        self, content: ExtractedContent, max_tokens: int = 500, overlap: int = 50
    ) -> List[ChunkDTO]:
        chunks: List[ChunkDTO] = []
        chunk_idx = 0

        # If we have structured pages, chunk by page
        if content.pages:
            for page in content.pages:
                page_text = page.text.strip()
                if not page_text:
                    continue

                page_sentences = self._split_into_sentences(page_text)
                current_chunk_sentences: List[str] = []
                current_tokens = 0

                for sentence in page_sentences:
                    sentence_tokens = self._estimate_tokens(sentence)
                    if current_tokens + sentence_tokens > max_tokens and current_chunk_sentences:
                        # Flush current chunk
                        chunk_content = " ".join(current_chunk_sentences)
                        chunks.append(
                            ChunkDTO(
                                chunk_index=chunk_idx,
                                content=chunk_content,
                                page_number=page.page_number,
                                token_count=current_tokens,
                            )
                        )
                        chunk_idx += 1

                        # Keep overlap sentences
                        overlap_sentences: List[str] = []
                        overlap_tokens = 0
                        for s in reversed(current_chunk_sentences):
                            s_tok = self._estimate_tokens(s)
                            if overlap_tokens + s_tok <= overlap:
                                overlap_sentences.insert(0, s)
                                overlap_tokens += s_tok
                            else:
                                break

                        current_chunk_sentences = overlap_sentences + [sentence]
                        current_tokens = overlap_tokens + sentence_tokens
                    else:
                        current_chunk_sentences.append(sentence)
                        current_tokens += sentence_tokens

                if current_chunk_sentences:
                    chunk_content = " ".join(current_chunk_sentences)
                    chunks.append(
                        ChunkDTO(
                            chunk_index=chunk_idx,
                            content=chunk_content,
                            page_number=page.page_number,
                            token_count=current_tokens,
                        )
                    )
                    chunk_idx += 1
        else:
            # Chunk full text
            full_text = content.full_text.strip()
            if not full_text:
                return []

            sentences = self._split_into_sentences(full_text)
            current_chunk_sentences: List[str] = []
            current_tokens = 0

            for sentence in sentences:
                sentence_tokens = self._estimate_tokens(sentence)
                if current_tokens + sentence_tokens > max_tokens and current_chunk_sentences:
                    chunk_content = " ".join(current_chunk_sentences)
                    chunks.append(
                        ChunkDTO(
                            chunk_index=chunk_idx,
                            content=chunk_content,
                            page_number=None,
                            token_count=current_tokens,
                        )
                    )
                    chunk_idx += 1

                    # Overlap
                    overlap_sentences: List[str] = []
                    overlap_tokens = 0
                    for s in reversed(current_chunk_sentences):
                        s_tok = self._estimate_tokens(s)
                        if overlap_tokens + s_tok <= overlap:
                            overlap_sentences.insert(0, s)
                            overlap_tokens += s_tok
                        else:
                            break

                    current_chunk_sentences = overlap_sentences + [sentence]
                    current_tokens = overlap_tokens + sentence_tokens
                else:
                    current_chunk_sentences.append(sentence)
                    current_tokens += sentence_tokens

            if current_chunk_sentences:
                chunk_content = " ".join(current_chunk_sentences)
                chunks.append(
                    ChunkDTO(
                        chunk_index=chunk_idx,
                        content=chunk_content,
                        page_number=None,
                        token_count=current_tokens,
                    )
                )

        return chunks
