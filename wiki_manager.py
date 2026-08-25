"""
Wiki Manager Module for LLM Wiki

Handles the core workflows defined by Andrej Karpathy:
1. Ingestion: Reads sources from /sources, builds/updates wiki pages incrementally.
2. Indexing: Auto-maintains wiki/index.md (catalog by categories: Entities, Concepts, Syntheses, Sources).
3. Logging: Chronological append-only record in wiki/log.md (## [YYYY-MM-DD HH:MM] operation | detail).
4. Querying: Answers questions against wiki content, with option to save synthesis back into wiki.
5. Linting: Health checks (broken links, orphan pages, contradictions, missing connections).
"""

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

from config import (
    SOURCES_DIR,
    WIKI_DIR,
    WIKI_ENTITIES_DIR,
    WIKI_CONCEPTS_DIR,
    WIKI_SOURCES_DIR,
    WIKI_SYNTHESES_DIR,
    INDEX_FILE,
    LOG_FILE,
    MANIFEST_FILE,
    init_environment,
)
from llm_client import call_llm


def get_timestamp() -> str:
    """Returns current date and time formatted as YYYY-MM-DD HH:MM."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get_target_wiki_path(filename: str) -> Path:
    """
    Returns the appropriate destination Path in wiki subdirectories (entities, concepts, sources, syntheses)
    based on the filename or prefix.
    """
    clean_name = filename.strip()
    basename = Path(clean_name).name

    if clean_name.startswith("entities/") or basename.startswith("Entite_") or basename.startswith("Entity_"):
        return WIKI_ENTITIES_DIR / basename
    elif clean_name.startswith("concepts/") or basename.startswith("Concept_"):
        return WIKI_CONCEPTS_DIR / basename
    elif clean_name.startswith("sources/") or basename.startswith("Source_"):
        return WIKI_SOURCES_DIR / basename
    elif clean_name.startswith("syntheses/") or basename.startswith("Synthesis_"):
        return WIKI_SYNTHESES_DIR / basename
    else:
        # Fallback heuristic based on name
        lower_name = basename.lower()
        if "concept" in lower_name:
            return WIKI_CONCEPTS_DIR / basename
        elif "entite" in lower_name or "entity" in lower_name:
            return WIKI_ENTITIES_DIR / basename
        elif "source" in lower_name:
            return WIKI_SOURCES_DIR / basename
        elif "synthes" in lower_name:
            return WIKI_SYNTHESES_DIR / basename
        return WIKI_SYNTHESES_DIR / basename


def migrate_existing_wiki_files() -> None:
    """
    Moves any legacy markdown files in /wiki root into their respective
    subdirectories (entities, concepts, sources, syntheses).
    """
    init_environment()
    if not WIKI_DIR.exists():
        return
    for filepath in WIKI_DIR.glob("*.md"):
        if filepath.name in ["index.md", "log.md"]:
            continue
        target_path = get_target_wiki_path(filepath.name)
        if filepath.resolve() != target_path.resolve():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            filepath.rename(target_path)


def append_to_log(operation: str, title: str, details: str = "") -> None:
    """
    Appends an entry to log.md using Karpathy's chronological format:
    ## [YYYY-MM-DD HH:MM] operation | title
    """
    init_environment()
    timestamp = get_timestamp()
    log_entry = f"## [{timestamp}] {operation} | {title}\n"
    if details:
        log_entry += f"{details.strip()}\n\n"
    else:
        log_entry += "\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)


def load_manifest() -> Dict[str, dict]:
    """Loads manifest of processed source files."""
    init_environment()
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_manifest(manifest: Dict[str, dict]) -> None:
    """Saves manifest of processed source files."""
    init_environment()
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def calculate_file_hash(filepath: Path) -> str:
    """Computes SHA256 hash of a source file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def get_all_wiki_pages() -> Dict[str, str]:
    """
    Returns a map of {relative_posix_path: file_content} for all markdown files
    in /wiki and its subdirectories except index.md and log.md.
    """
    init_environment()
    migrate_existing_wiki_files()
    pages = {}
    for filepath in WIKI_DIR.rglob("*.md"):
        if filepath.name in ["index.md", "log.md"]:
            continue
        rel_path = filepath.relative_to(WIKI_DIR).as_posix()
        pages[rel_path] = filepath.read_text(encoding="utf-8")
    return pages


def update_index_md() -> None:
    """
    Scans all wiki pages across /wiki subdirectories and re-builds wiki/index.md,
    categorizing pages into Entities, Concepts, Syntheses, and Source Summaries.
    """
    pages = get_all_wiki_pages()
    
    entities = []
    concepts = []
    syntheses = []
    sources = []

    for rel_path, content in sorted(pages.items()):
        # Extract title from first # header or fallback to filename stem
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        basename = Path(rel_path).stem
        title = match.group(1).strip() if match else basename.replace("_", " ")

        # Extract one-line summary (first non-header non-empty line or > blockquote)
        summary = ""
        for line in content.splitlines():
            line_str = line.strip()
            if line_str and not line_str.startswith("#") and not line_str.startswith("---"):
                summary = line_str.lstrip("> ").strip()
                if len(summary) > 120:
                    summary = summary[:117] + "..."
                break

        link_entry = f"- [{title}]({rel_path}) - {summary}" if summary else f"- [{title}]({rel_path})"

        # Categorize by subdirectory prefix or tags
        if rel_path.startswith("sources/") or basename.startswith("Source_") or "Type: Source Summary" in content:
            sources.append(link_entry)
        elif rel_path.startswith("entities/") or basename.startswith("Entite_") or basename.startswith("Entity_") or "Type: Entity" in content:
            entities.append(link_entry)
        elif rel_path.startswith("concepts/") or basename.startswith("Concept_") or "Type: Concept" in content:
            concepts.append(link_entry)
        else:
            syntheses.append(link_entry)

    index_content = "# Index du LLM Wiki\n\n"
    index_content += f"*Dernière mise à jour : {get_timestamp()} | Total de pages : {len(pages)}*\n\n"

    index_content += "## Entités\n"
    index_content += "\n".join(entities) + "\n\n" if entities else "*Aucune fiche d'entité pour le moment.*\n\n"

    index_content += "## Concepts\n"
    index_content += "\n".join(concepts) + "\n\n" if concepts else "*Aucune fiche de concept pour le moment.*\n\n"

    index_content += "## Synthèses & Guides Thématiques\n"
    index_content += "\n".join(syntheses) + "\n\n" if syntheses else "*Aucune fiche de synthèse pour le moment.*\n\n"

    index_content += "## Résumés de Sources\n"
    index_content += "\n".join(sources) + "\n\n" if sources else "*Aucun résumé de source pour le moment.*\n\n"

    INDEX_FILE.write_text(index_content, encoding="utf-8")


def read_docx_file(filepath: Path) -> str:
    """Extracts text content from Word (.docx) documents using pure-Python zipfile & ElementTree."""
    import zipfile
    import xml.etree.ElementTree as ET
    try:
        with zipfile.ZipFile(filepath, "r") as zip_ref:
            xml_content = zip_ref.read("word/document.xml")
        
        tree = ET.fromstring(xml_content)
        paragraphs = []
        for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            texts = [t.text for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if t.text]
            if texts:
                paragraphs.append("".join(texts).strip())
        return "\n\n".join(paragraphs)
    except Exception as e:
        print(f"⚠️  Error reading Word document {filepath.name}: {e}")
        return ""



def read_pdf_file(filepath: Path) -> str:
    """Extracts text content from PDF (.pdf) documents using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        text_pages = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted and extracted.strip():
                text_pages.append(extracted.strip())
        return "\n\n".join(text_pages)
    except Exception as e:
        print(f"⚠️  Error reading PDF document {filepath.name}: {e}")
        return ""


def read_source_file(filepath: Path) -> str:
    """Reads source file text content safely, supporting text files, Word (.docx), and PDF (.pdf) documents."""
    ext = filepath.suffix.lower()
    if ext == ".docx":
        return read_docx_file(filepath)
    elif ext == ".pdf":
        return read_pdf_file(filepath)
        
    try:
        return filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return filepath.read_text(encoding="latin-1", errors="replace")




def ingest_new_sources() -> List[str]:
    """
    Detects un-ingested or modified source files in /sources,
    uses the LLM to summarize and integrate them into the Wiki,
    and updates index.md and log.md incrementally.
    """
    init_environment()
    manifest = load_manifest()
    source_files = list(SOURCES_DIR.glob("*.*"))

    # Exclude system or hidden files
    valid_sources = [f for f in source_files if not f.name.startswith(".")]

    if not valid_sources:
        print("\nℹ️  No files found in /sources directory.")
        print(f"   Place source documents (e.g. .txt, .md) in: {SOURCES_DIR}\n")
        return []

    ingested_titles = []

    for source_path in valid_sources:
        file_hash = calculate_file_hash(source_path)
        filename = source_path.name

        # Incremental check: skip if file hash hasn't changed
        if filename in manifest and manifest[filename].get("hash") == file_hash:
            continue

        print(f"\n🔄 Processing source: {filename}...")
        source_text = read_source_file(source_path)
        
        existing_index = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else ""

        # System prompt for source ingestion in French with subdirectories
        system_prompt = (
            "Tu es un gestionnaire expert de LLM Wiki. Ta mission est d'analyser un document source brut "
            "et de mettre à jour le Wiki Markdown persistent structuré en sous-dossiers (entities/, concepts/, sources/).\n"
            "CONSIGNE DE LANGUE IMPÉRATIVE :\n"
            "Tu dois rédiger TOUS les contenus, titres, résumés, concepts et entités STRICTEMENT EN FRANÇAIS.\n\n"
            "Directives :\n"
            "1. Extrais les faits clés, entités, concepts et éléments de synthèse.\n"
            "2. Génère un contenu Markdown propre et clair.\n"
            "3. Interconnecte les pages du wiki en utilisant des liens Markdown : [Titre](entities/Entite_Nom.md) ou [Titre](concepts/Concept_Nom.md).\n"
            "4. Retourne UNIQUEMENT un objet JSON valide structuré comme suit :\n"
            "{\n"
            '  "source_summary_filename": "Source_<Nom>.md",\n'
            '  "source_summary_content": "# Titre du document\\n\\nRésumé détaillé en français...",\n'
            '  "wiki_updates": [\n'
            '     {"filename": "Concept_<Nom>.md", "content": "# Nom du Concept\\n\\nExplication détaillée en français..."},\n'
            '     {"filename": "Entite_<Nom>.md", "content": "# Nom de l\'Entité\\n\\nPrésentation en français..."}\n'
            "  ]\n"
            "}\n"
        )

        user_prompt = (
            f"NOM DU FICHIER SOURCE : {filename}\n\n"
            f"INDEX ACTUEL DU WIKI :\n{existing_index}\n\n"
            f"CONTENU DU DOCUMENT SOURCE :\n{source_text[:12000]}\n\n"
            "Synthétise cette source en français, génère la fiche de résumé de source et crée/mets à jour les fiches de concepts et d'entités en français. "
            "Réponds uniquement en JSON valide."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response_str = call_llm(messages, temperature=0.2)
        
        # Clean JSON markdown fences if present
        cleaned_str = re.sub(r"^```json\s*", "", response_str, flags=re.MULTILINE)
        cleaned_str = re.sub(r"```$", "", cleaned_str, flags=re.MULTILINE).strip()

        try:
            data = json.loads(cleaned_str)
        except json.JSONDecodeError:
            # Fallback if LLM outputted raw text instead of JSON
            safe_stem = re.sub(r"[^\w\-]", "_", source_path.stem)
            data = {
                "source_summary_filename": f"Source_{safe_stem}.md",
                "source_summary_content": f"# Summary of {filename}\n\n" + response_str,
                "wiki_updates": []
            }

        # Write Source Summary page into wiki/sources/
        summary_filename = data.get("source_summary_filename", f"Source_{source_path.stem}.md")
        summary_path = get_target_wiki_path(summary_filename)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(data.get("source_summary_content", ""), encoding="utf-8")
        summary_rel = summary_path.relative_to(WIKI_DIR).as_posix()
        print(f"   ✓ Created/Updated: {summary_rel}")

        # Write/Update Entity and Concept pages in their respective subdirectories
        for update in data.get("wiki_updates", []):
            page_filename = update.get("filename")
            page_content = update.get("content")
            if page_filename and page_content:
                page_path = get_target_wiki_path(page_filename)
                page_path.parent.mkdir(parents=True, exist_ok=True)
                page_rel = page_path.relative_to(WIKI_DIR).as_posix()
                
                # Merge if file already exists
                if page_path.exists():
                    existing_text = page_path.read_text(encoding="utf-8")
                    merged_content = existing_text + f"\n\n---\n### Update from {filename} ({get_timestamp()})\n\n" + page_content
                    page_path.write_text(merged_content, encoding="utf-8")
                    print(f"   ✓ Updated existing page: {page_rel}")
                else:
                    page_path.write_text(page_content, encoding="utf-8")
                    print(f"   ✓ Created page: {page_rel}")

        # Update manifest
        manifest[filename] = {
            "hash": file_hash,
            "ingested_at": get_timestamp(),
            "summary_page": summary_rel,
        }
        save_manifest(manifest)

        # Append to log.md (Karpathy spec)
        append_to_log("ingest", filename, f"Created summary {summary_rel} and integrated concepts into wiki subdirectories.")
        ingested_titles.append(filename)

    # Re-build index.md
    update_index_md()
    print(f"\n✅ Ingestion complete! Processed {len(ingested_titles)} new/updated source(s).")
    return ingested_titles


def query_wiki(query_text: str) -> Tuple[str, List[str]]:
    """
    Queries the wiki by searching index.md and relevant wiki pages,
    synthesizes a response with citations, and returns (response_text, relevant_filenames).
    """
    init_environment()
    index_text = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else ""
    pages = get_all_wiki_pages()

    if not pages:
        return (
            "The Wiki is currently empty. Please add source files to /sources and run 'ingest' first.",
            []
        )

    # Step 1: Let LLM pick the most relevant wiki pages based on index
    selection_prompt = (
        "Given the user query and the Wiki Index below, list the relative filenames of up to 5 relevant wiki pages "
        "needed to answer the query.\n"
        "Return ONLY a JSON array of string relative filenames, e.g. [\"concepts/Concept_X.md\", \"sources/Source_Y.md\"]."
    )
    selection_messages = [
        {"role": "system", "content": selection_prompt},
        {"role": "user", "content": f"QUERY: {query_text}\n\nWIKI INDEX:\n{index_text}"}
    ]

    sel_response = call_llm(selection_messages, temperature=0.1)
    sel_cleaned = re.sub(r"^```json\s*", "", sel_response, flags=re.MULTILINE)
    sel_cleaned = re.sub(r"```$", "", sel_cleaned, flags=re.MULTILINE).strip()

    try:
        relevant_files = json.loads(sel_cleaned)
        if not isinstance(relevant_files, list):
            relevant_files = list(pages.keys())[:5]
    except Exception:
        relevant_files = list(pages.keys())[:5]

    # Retrieve context from chosen files (handling both relative path and basename lookup)
    context_blocks = []
    normalized_relevant = []
    for fn in relevant_files:
        matched_key = None
        if fn in pages:
            matched_key = fn
        else:
            base = Path(fn).name
            for p_key in pages:
                if Path(p_key).name == base:
                    matched_key = p_key
                    break
        
        if matched_key:
            context_blocks.append(f"--- FILE: {matched_key} ---\n{pages[matched_key]}")
            normalized_relevant.append(matched_key)

    if not context_blocks:
        # Fallback to first 5 pages if selection failed
        for fn, content in list(pages.items())[:5]:
            context_blocks.append(f"--- FILE: {fn} ---\n{content}")
            normalized_relevant.append(fn)

    context_str = "\n\n".join(context_blocks)

    # Step 2: Synthesize answer in French with citations
    synth_prompt = (
        "Tu es l'Assistant LLM Wiki. Réponds à la question de l'utilisateur STRICTEMENT EN FRANÇAIS en t'appuyant uniquement sur les pages du Wiki fournies.\n"
        "Cite les pages du wiki pertinentes avec des liens Markdown standard : [Titre de la Page](subfolder/NomFichier.md).\n"
        "Si des informations manquent, précise clairement ce qui est connu et les lacunes d'information identifiées."
    )
    synth_messages = [
        {"role": "system", "content": synth_prompt},
        {"role": "user", "content": f"QUESTION DE L'UTILISATEUR : {query_text}\n\nCONTEXTE WIKI :\n{context_str}"}
    ]

    answer = call_llm(synth_messages, temperature=0.3)

    # Log query operation
    append_to_log("query", query_text, f"Synthesized answer using {len(normalized_relevant)} page(s).")
    
    return answer, normalized_relevant


def save_synthesis_to_wiki(title: str, content: str) -> str:
    """
    Saves a synthesized query response back into the Wiki as a persistent Synthesis page in /wiki/syntheses/.
    Compounding knowledge as described by Karpathy.
    """
    safe_title = re.sub(r"[^\w\-]", "_", title.strip())
    filename = f"Synthesis_{safe_title}.md"
    file_path = WIKI_SYNTHESES_DIR / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    formatted_content = f"# Synthesis: {title}\n\n"
    formatted_content += f"*Generated: {get_timestamp()}*\n\n"
    formatted_content += content.strip() + "\n"

    file_path.write_text(formatted_content, encoding="utf-8")
    
    update_index_md()
    rel_path = f"syntheses/{filename}"
    append_to_log("synthesis", title, f"Filed query answer back into wiki as {rel_path}.")
    return rel_path


def lint_wiki() -> str:
    """
    Performs a health check on the Wiki:
    - Identifies broken links across subdirectories
    - Identifies orphan pages
    - Asks LLM to find contradictions, stale claims, and content gaps
    """
    init_environment()
    pages = get_all_wiki_pages()
    
    if not pages:
        return "The Wiki is empty. Nothing to lint."

    existing_rel_paths = set(pages.keys())
    existing_basenames = {Path(p).name: p for p in pages.keys()}
    existing_rel_paths.add("index.md")
    existing_rel_paths.add("log.md")

    broken_links = []
    incoming_links: Dict[str, Set[str]] = {fn: set() for fn in pages.keys()}

    # Scan for markdown links: [Text](Target.md) or [Text](folder/Target.md)
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")

    for src_file, content in pages.items():
        for match in link_pattern.finditer(content):
            raw_target = match.group(2).strip()
            # Normalize target relative path
            target_norm = raw_target.lstrip("./").replace("\\", "/")
            target_base = Path(target_norm).name

            target_match = None
            if target_norm in existing_rel_paths:
                target_match = target_norm
            elif target_base in existing_basenames:
                target_match = existing_basenames[target_base]

            if not target_match and target_base not in ["index.md", "log.md"]:
                broken_links.append((src_file, raw_target))
            elif target_match and target_match in incoming_links:
                incoming_links[target_match].add(src_file)

    # Check for orphan pages (pages not linked by any other page)
    orphan_pages = [fn for fn, links in incoming_links.items() if len(links) == 0]

    # LLM Lint pass for contradictions & content gaps
    sample_context = "\n\n".join([f"=== {fn} ===\n{content[:1500]}" for fn, content in pages.items()])
    
    lint_prompt = (
        "Tu es l'Auditeur du LLM Wiki. Effectue un contrôle de santé (health check) sur l'ensemble des pages du wiki ci-dessous.\n"
        "CONSIGNE DE LANGUE : Rédige ton rapport d'audit INTEGRALEMENT EN FRANÇAIS.\n"
        "Vérifie :\n"
        "1. Les contradictions ou affirmations conflictuelles entre pages\n"
        "2. Les informations obsolètes ou incomplètes\n"
        "3. Les concepts manquants ou les liens croisés à créer\n"
        "4. Les questions suggérées ou sources complémentaires à rechercher\n"
        "Formate ta réponse sous forme de Rapport d'Audit Markdown propre et structuré en français."
    )

    lint_messages = [
        {"role": "system", "content": lint_prompt},
        {"role": "user", "content": f"ÉCHANTILLON DU CONTENU WIKI :\n{sample_context}"}
    ]

    llm_analysis = call_llm(lint_messages, temperature=0.2)

    # Reconstruct full report in French
    report = "# Rapport d'Audit & Contrôle Santé du LLM Wiki\n\n"
    report += f"*Exécuté le : {get_timestamp()}*\n\n"

    report += "## Intégrité Structurelle\n"
    if broken_links:
        report += "### ❌ Liens brisés détectés :\n"
        for src, target in broken_links:
            report += f"- Dans `{src}` -> fait référence au fichier manquant `{target}`\n"
        report += "\n"
    else:
        report += "✓ Aucun lien interne brisé n'a été détecté.\n\n"

    if orphan_pages:
        report += "### ⚠️ Pages Orphelines (Aucun lien entrant) :\n"
        for orphan in orphan_pages:
            report += f"- `{orphan}`\n"
        report += "\n"
    else:
        report += "✓ Aucune page orpheline détectée (toutes les pages sont reliées).\n\n"

    report += "## Audit Sémantique par LLM & Recommandations\n\n"
    report += llm_analysis.strip() + "\n"

    append_to_log("lint", "Wiki Health Check", f"Found {len(broken_links)} broken links and {len(orphan_pages)} orphan pages.")
    
    return report


def get_wiki_status() -> Dict[str, object]:
    """Returns statistics about the current wiki state."""
    init_environment()
    manifest = load_manifest()
    pages = get_all_wiki_pages()

    last_log_entries = []
    if LOG_FILE.exists():
        log_lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        log_headers = [line for line in log_lines if line.startswith("## [")]
        last_log_entries = log_headers[-5:]

    return {
        "sources_count": len(manifest),
        "wiki_pages_count": len(pages),
        "has_index": INDEX_FILE.exists(),
        "has_log": LOG_FILE.exists(),
        "last_log_entries": last_log_entries,
    }


def reset_wiki(keep_sources: bool = True) -> None:
    """
    Resets the Wiki to a clean state.
    Deletes all wiki pages across subdirectories, manifest, log.md, and index.md.
    If keep_sources is False, also clears the /sources directory.
    """
    import shutil
    if WIKI_DIR.exists():
        for item in WIKI_DIR.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    if not keep_sources and SOURCES_DIR.exists():
        for file in SOURCES_DIR.glob("*"):
            if file.is_file() and not file.name.startswith("."):
                file.unlink()

    # Re-initialize clean index.md, log.md and subdirectories
    init_environment()


