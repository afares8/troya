"""Project code indexer with TF-IDF for intelligent context retrieval."""

import json
import math
import re
from pathlib import Path
from typing import Any

INDEX_FILE = Path.home() / ".config" / "cascade-cli" / "code_index.json"


def tokenize(text: str) -> list[str]:
    return re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', text.lower())


def compute_tfidf(documents: list[str]) -> tuple[dict, dict]:
    """Compute TF-IDF vectors for documents. Returns (doc_vectors, idf)."""
    tokenized = [tokenize(d) for d in documents]
    vocab = set()
    for tokens in tokenized:
        vocab.update(tokens)

    # IDF
    idf = {}
    for term in vocab:
        doc_count = sum(1 for tokens in tokenized if term in tokens)
        idf[term] = math.log(len(documents) / (1 + doc_count))

    # TF-IDF vectors
    vectors = []
    for tokens in tokenized:
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        vec = {t: (count / len(tokens)) * idf.get(t, 0) for t, count in tf.items()}
        vectors.append(vec)

    return vectors, idf


def cosine_similarity(v1: dict, v2: dict) -> float:
    dot = sum(v1.get(t, 0) * v2.get(t, 0) for t in set(v1) | set(v2))
    norm1 = math.sqrt(sum(x ** 2 for x in v1.values()))
    norm2 = math.sqrt(sum(x ** 2 for x in v2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class CodeIndex:
    """Simple TF-IDF based code indexer."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.documents: list[str] = []
        self.paths: list[str] = []
        self.vectors: list[dict] = []
        self.idf: dict = {}
        self.loaded = False

    def build(self, max_files: int = 200) -> None:
        """Index all code files in the project."""
        print(f"{Colors.CYAN}Indexing project...{Colors.RESET}", end=" ")
        self.documents = []
        self.paths = []
        count = 0
        for path in self.root.rglob("*"):
            if count >= max_files:
                break
            if not path.is_file():
                continue
            if path.stat().st_size > 50_000:
                continue
            if path.suffix not in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt", ".scala", ".md", ".json", ".yaml", ".yml", ".toml", ".sh", ".sql"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            self.paths.append(str(path.relative_to(self.root)))
            self.documents.append(content)
            count += 1

        if self.documents:
            self.vectors, self.idf = compute_tfidf(self.documents)
            print(f"{Colors.GREEN}{len(self.documents)} files indexed{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}No files indexed{Colors.RESET}")
        self.loaded = True

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Search for files semantically similar to the query."""
        if not self.loaded or not self.documents:
            return []
        query_tokens = tokenize(query)
        query_tf = {}
        for t in query_tokens:
            query_tf[t] = query_tf.get(t, 0) + 1
        query_vec = {t: (count / len(query_tokens)) * self.idf.get(t, 0) for t, count in query_tf.items()}

        scores = []
        for i, vec in enumerate(self.vectors):
            score = cosine_similarity(query_vec, vec)
            if score > 0.01:
                scores.append((self.paths[i], score))
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]

    def get_snippet(self, path: str, query: str, context_lines: int = 3) -> str:
        """Get a relevant snippet from a file matching the query."""
        file_path = self.root / path
        if not file_path.exists():
            return ""
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            return ""
        query_lower = query.lower()
        for i, line in enumerate(lines):
            if query_lower in line.lower():
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                return "\n".join(lines[start:end])
        return "\n".join(lines[:context_lines * 2])


# For import in main.py
from .ui import Colors
