import asyncio
import json
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from backend.app.core.database import async_session_factory

# Force UTF-8 for terminal output
sys.stdout.reconfigure(encoding='utf-8')

async def visualize(search_term: str = None, list_all: bool = False):
    async with async_session_factory() as s:
        if list_all:
            res = await s.execute(text("SELECT id, title, record_type, status, created_at FROM documents ORDER BY created_at DESC LIMIT 15;"))
            docs = res.fetchall()
            print("\n=======================================================")
            print("             HISTORICAL ARCHIVE DOCUMENTS             ")
            print("=======================================================")
            for i, d in enumerate(docs, 1):
                print(f"{i}. [{d.record_type.upper()}] {d.title}")
                print(f"   ID: {d.id} | Status: {d.status}")
            print("\nRun: python scripts/demo_db_visualize.py --id <ID>")
            return

        if search_term:
            res = await s.execute(
                text("SELECT id, title FROM documents WHERE title ILIKE :term OR id::text ILIKE :term LIMIT 1;"),
                {"term": f"%{search_term}%"}
            )
        else:
            res = await s.execute(text("SELECT id, title FROM documents ORDER BY created_at DESC LIMIT 1;"))
        
        doc = res.first()
        if not doc:
            print(f"No document found matching: {search_term or 'any'}")
            return
            
        doc_id = doc.id
        print("=======================================================")
        print("      DATABASE VISUALIZER: ARCHIVE CLIENT DEMO        ")
        print("=======================================================\n")
        print(f"📄 DOCUMENT: {doc.title}")
        print(f"🔑 Primary Key (UUID): {doc_id}\n")
        
        # 1. Extracted Metadata
        meta = await s.execute(text(f"""
            SELECT date_start, language, organization, subjects, locations, creators, ai_metadata 
            FROM document_metadata 
            WHERE document_id = '{doc_id}';
        """))
        m = meta.first()
        print("=======================================================")
        print("1. EXTRACTED METADATA  [Table: document_metadata]")
        print("=======================================================")
        if m:
            print(f"• Language:     {m.language}")
            print(f"• Date (Start): {m.date_start or 'N/A'}")
            print(f"• Organization: {m.organization or 'N/A'}")
            print(f"• AI Extracted JSON (Key Attributes):")
            ai_data = m.ai_metadata or {}
            for k, v in list(ai_data.items())[:8]:
                print(f"    - {k}: {v}")
        else:
            print("No metadata recorded.")
        print()

        # 2. Extracted Entities
        ents = await s.execute(text(f"""
            SELECT e.name, e.entity_type, de.confidence
            FROM document_entities de
            JOIN entities e ON e.id = de.entity_id
            WHERE de.document_id = '{doc_id}'
            LIMIT 6;
        """))
        ent_list = ents.fetchall()
        print("=======================================================")
        print("2. EXTRACTED ENTITIES  [Tables: entities, document_entities]")
        print("=======================================================")
        if ent_list:
            for e in ent_list:
                conf = f" (Confidence: {float(e.confidence):.2f})" if e.confidence else ""
                print(f"• {e.name}  [{e.entity_type}]{conf}")
        else:
            print("No entities linked for this document.")
        print()

        # 3. Knowledge Graph Relationships
        rels = await s.execute(text(f"""
            SELECT r.relationship_type, s.name AS source_name, t.name AS target_name
            FROM relationships r
            JOIN entities s ON s.id = r.source_entity_id
            JOIN entities t ON t.id = r.target_entity_id
            JOIN document_entities de ON (de.entity_id = s.id OR de.entity_id = t.id)
            WHERE de.document_id = '{doc_id}'
            LIMIT 5;
        """))
        rel_list = rels.fetchall()
        print("=======================================================")
        print("3. KNOWLEDGE GRAPH RELATIONS  [Table: relationships]")
        print("=======================================================")
        if rel_list:
            for r in rel_list:
                print(f"• ({r.source_name}) ──[{r.relationship_type}]──> ({r.target_name})")
        else:
            print("No knowledge graph links recorded.")
        print()

        # 4. Chunks
        chunks = await s.execute(text(f"""
            SELECT id, chunk_index, page_number, token_count, content 
            FROM document_chunks 
            WHERE document_id = '{doc_id}' 
            ORDER BY chunk_index ASC 
            LIMIT 2;
        """))
        chunk_list = chunks.fetchall()
        print("=======================================================")
        print("4. DOCUMENT CHUNKS  [Table: document_chunks]")
        print("=======================================================")
        if chunk_list:
            for c in chunk_list:
                clean_preview = " ".join(c.content.split())[:130]
                print(f"• Chunk #{c.chunk_index} (Page: {c.page_number or 1}, Tokens: {c.token_count or 'N/A'}):")
                print(f"  Chunk UUID: {c.id}")
                print(f"  Text Preview: \"{clean_preview}...\"")
        else:
            print("No chunks found.")
            return
        print()

        # 5. Semantic Vector Embeddings
        first_chunk_id = chunk_list[0].id
        embeddings = await s.execute(text(f"""
            SELECT model_name, dimension, embedding 
            FROM chunk_embeddings 
            WHERE chunk_id = '{first_chunk_id}' 
            LIMIT 1;
        """))
        e = embeddings.first()
        print("=======================================================")
        print("5. SEMANTIC EMBEDDING (pgvector)  [Table: chunk_embeddings]")
        print("=======================================================")
        if e:
            vec_str = str(e.embedding)
            dimensions = e.dimension or 768
            preview_floats = vec_str.strip("[]").split(",")[:6]
            formatted_vec = ", ".join([f"{float(x):.5f}" for x in preview_floats if x.strip()])
            print(f"• Embedding Model: {e.model_name}")
            print(f"• Vector Dimensions: {dimensions} dimensions (native pgvector)")
            print(f"• Mathematical Semantic Representation for Chunk #{chunk_list[0].chunk_index}:")
            print(f"  [{formatted_vec}, ... ]")
        else:
            print("No vector embeddings found.")
        print("=======================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Database Visualizer for Demo")
    parser.add_argument("--search", "-s", type=str, help="Search document by title or UUID substring")
    parser.add_argument("--id", type=str, help="Document UUID")
    parser.add_argument("--list", "-l", action="store_true", help="List available documents in the archive")
    args = parser.parse_args()

    target = args.id or args.search
    asyncio.run(visualize(search_term=target, list_all=args.list))
