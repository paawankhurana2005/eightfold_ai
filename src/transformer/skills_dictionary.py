"""Skill alias dictionary -> canonical skill names.

Keys are lowercased aliases; values are the canonical display name. Unknown skills are
NOT dropped — they pass through title-cased (see ``normalize/skills.py``). This is a
small, deliberately readable seed list; in production it would be a managed taxonomy.
"""

from __future__ import annotations

# canonical name -> list of aliases (all matched case-insensitively)
_CANONICAL: dict[str, list[str]] = {
    "JavaScript": ["js", "javascript", "ecmascript", "java script"],
    "TypeScript": ["ts", "typescript", "type script"],
    "Python": ["python", "py", "python3"],
    "Java": ["java"],
    "C++": ["c++", "cpp", "cplusplus"],
    "C#": ["c#", "csharp", "c sharp"],
    "Go": ["go", "golang"],
    "Rust": ["rust", "rust-lang"],
    "Ruby": ["ruby"],
    "PHP": ["php"],
    "SQL": ["sql"],
    "PostgreSQL": ["postgres", "postgresql", "psql"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongo", "mongodb"],
    "Redis": ["redis"],
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node", "node.js", "nodejs"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi", "fast api"],
    "Kubernetes": ["k8s", "kubernetes", "kube"],
    "Docker": ["docker"],
    "AWS": ["aws", "amazon web services"],
    "GCP": ["gcp", "google cloud", "google cloud platform"],
    "Azure": ["azure", "microsoft azure"],
    "Terraform": ["terraform", "tf"],
    "Machine Learning": ["ml", "machine learning", "machine-learning"],
    "Deep Learning": ["dl", "deep learning"],
    "TensorFlow": ["tensorflow", "tf2"],
    "PyTorch": ["pytorch", "torch"],
    "GraphQL": ["graphql", "gql"],
    "REST": ["rest", "rest api", "restful"],
    "Git": ["git"],
}


def _build_alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for canonical, aliases in _CANONICAL.items():
        index[canonical.lower()] = canonical
        for alias in aliases:
            index[alias.lower()] = canonical
    return index


# alias (lowercased) -> canonical name
ALIAS_INDEX: dict[str, str] = _build_alias_index()
