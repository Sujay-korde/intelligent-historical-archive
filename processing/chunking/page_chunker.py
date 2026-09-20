import re
from typing import List

from processing.base import ExtractedContent
from processing.chunking.base import BaseChunker, ChunkDTO


class PageChunker(BaseChunker):
    """
    Page-level archival chunker.
    Emits exactly one chunk per archival page or leaf asset.
    Preserves exact archival leaf boundaries, which is ideal for historical manuscripts,
    letters, registers, maps, and photographic records.
    If an individual page exceeds max_tokens, it performs graceful sentence-level splitting.
    """
    strategy_name: str = "PageChunker"

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def chunk(
        self, content: ExtractedContent, max_tokens: int = 500, overlap: int = 50
    ) -> List[ChunkDTO]:
        chunks: List[ChunkDTO] = []
        chunk_idx = 0

        # If structured pages exist, process each page
        if content.pages:
            for page in content.pages:
                page_text = page.text.strip()
                if not page_text:
                    continue

                tokens = self._estimate_tokens(page_text)
                # If page fits within token threshold, retain as a single unified page chunk
                if tokens <= max_tokens:
                    chunks.append(
                        ChunkDTO(
                            chunk_index=chunk_idx,
                            content=page_text,
                            page_number=page.page_number,
                            token_count=tokens,
                        )
                    )
                    chunk_idx += 1
                else:
                    # Gracefully break large page by sentences
                    sentence_end = re.compile(r"(?<=[.!?])\s+")
                    sentences = [s.strip() for s in sentence_end.split(page_text) if s.strip()]
                    current_sentences = []
                    current_toks = 0

                    for s in sentences:
                        s_tok = self._estimate_tokens(s)
                        if current_toks + s_tok > max_tokens and current_sentences:
                            chunks.append(
                                ChunkDTO(
                                    chunk_index=chunk_idx,
                                    content=" ".join(current_sentences),
                                    page_number=page.page_number,
                                    token_count=current_toks,
                                )
                            )
                            chunk_idx += 1
                            current_sentences = [s]
                            current_toks = s_tok
                        else:
                            current_sentences.append(s)
                            current_toks += s_tok

                    if current_sentences:
                        chunks.append(
                            ChunkDTO(
                                chunk_index=chunk_idx,
                                content=" ".join(current_sentences),
                                page_number=page.page_number,
                                token_count=current_toks,
                            )
                        )
                        chunk_idx += 1
        else:
            # Check for form-feed characters (\x0c) common in paginated text
            pages_raw = content.full_text.split("\x0c")
            for page_num, raw_p in enumerate(pages_raw, start=1):
                clean_p = raw_p.strip()
                if not clean_p:
                    continue
                tokens = self._estimate_tokens(clean_p)
                chunks.append(
                    ChunkDTO(
                        chunk_index=chunk_idx,
                        content=clean_p,
                        page_number=page_num if len(pages_raw) > 1 else None,
                        token_count=tokens,
                    )
                )
                chunk_idx += 1

        return chunks
