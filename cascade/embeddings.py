"""Real semantic embeddings using sentence-transformers."""

from pathlib import Path
from typing import Any

import numpy as np

from .ui import Colors, print_error, print_info, print_success

EMBEDDINGS_FILE = Path.home() / ".config" / "cascade-cli" / "embeddings.npz"


class EmbeddingIndex:
    """Semantic code search with sentence-transformers."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.paths: list[str] = []
        self.vectors: np.ndarray | None = None
        self.loaded = False

    def build(self, max_files: int = 200) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print_error("sentence-transformers not installed. Run: pip install sentence-transformers")
            return

        print_info("Loading embedding model (this may take a moment)...")
        model = SentenceTransformer("all-MiniLM-L6-v2")

        documents = []
        self.paths = []
        for path in self.root.rglob("*"):
            if len(documents) >= max_files:
                break
            if not path.is_file() or path.stat().st_size > 50_000:
                continue
            if path.suffix not in {".py", ".js", ".ts", ".md", ".go", ".rs", ".java", ".cpp", ".c", ".rb", ".php"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            documents.append(content[:2000])
            self.paths.append(str(path.relative_to(self.root)))

        if not documents:
            print_warning("No files to index")
            return

        print_info(f"Encoding {len(documents)} files...")
        self.vectors = model.encode(documents, show_progress_bar=False)
        np.savez(str(EMBEDDINGS_FILE), vectors=self.vectors, paths=self.paths)
        self.loaded = True
        print_success(f"Indexed {len(documents)} files with real embeddings")

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        if not self.loaded:
            if EMBEDDINGS_FILE.exists():
                data = np.load(str(EMBEDDINGS_FILE))
                self.vectors = data["vectors"]
                self.paths = data["paths"].tolist()
                self.loaded = True
            else:
                return []

        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            return []

        query_vec = model.encode([query])
        similarities = np.dot(self.vectors, query_vec.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(self.paths[i], float(similarities[i])) for i in top_indices if similarities[i] > 0.1]


def render_suggestion(suggestion: str) -> str:
    return f"{Colors.DIM}{suggestion}{Colors.RESET}"


from .ui import Colors, print_warning
