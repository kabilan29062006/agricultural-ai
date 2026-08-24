from pathlib import Path
import json
import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = BASE_DIR / "firebase-key.json"

if not KEY_FILE.exists():
    raise FileNotFoundError(
        "firebase-key.json was not found. Replace the placeholder with "
        "your Firebase service-account JSON."
    )

with KEY_FILE.open("r", encoding="utf-8") as f:
    key_data = json.load(f)

if not isinstance(key_data, dict) or key_data.get("_placeholder") is True:
    raise RuntimeError(
        "Replace the firebase-key.json placeholder with a real Firebase "
        "service-account JSON before starting the application."
    )

if not firebase_admin._apps:
    cred = credentials.Certificate(str(KEY_FILE))
    firebase_admin.initialize_app(cred)

db = firestore.client()


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def get_knowledge(max_documents=500):
    """
    Dynamically discovers root Firestore collections and their documents.
    No collection name is hardcoded. Documents are serialized with their
    collection/document paths so Gemini can infer relationships and
    abbreviations from surrounding context.
    """
    chunks = []
    count = 0

    for collection_ref in db.collections():
        collection_name = collection_ref.id
        try:
            docs = collection_ref.stream()
            for doc in docs:
                if count >= max_documents:
                    break
                payload = _json_safe(doc.to_dict() or {})
                chunks.append(
                    f"COLLECTION: {collection_name}\n"
                    f"DOCUMENT: {doc.id}\n"
                    f"PATH: {doc.reference.path}\n"
                    f"FIELDS_AND_VALUES:\n"
                    f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                )
                count += 1
            if count >= max_documents:
                break
        except Exception:
            continue

    return "\n\n---\n\n".join(chunks)
