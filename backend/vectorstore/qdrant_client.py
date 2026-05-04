"""Qdrant vector store operations for brand rule storage and retrieval."""

import hashlib
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
from backend.config import get_settings
from backend.services.llm import get_embedding

logger = logging.getLogger(__name__)

COLLECTION_NAME = "brand_rules"
VECTOR_SIZE = 1536  # text-embedding-3-small output dimensions
MIN_SCORE_THRESHOLD = 0.3  # discard rules with cosine similarity below this

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def ensure_collection():
    """Create the brand_rules collection if it doesn't exist."""
    client = _get_client()
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="guideline_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Created Qdrant collection: %s (with guideline_id index)", COLLECTION_NAME)


def store_rules(guideline_id: str, rules: list[dict]):
    """Embed and store parsed rules in Qdrant."""
    client = _get_client()
    ensure_collection()

    points = []
    for i, rule in enumerate(rules):
        text_to_embed = f"{rule['section']}: {rule['description']}"
        if rule.get("examples_bad"):
            text_to_embed += " Bad examples: " + "; ".join(rule["examples_bad"])
        if rule.get("examples_good"):
            text_to_embed += " Good examples: " + "; ".join(rule["examples_good"])

        vector = get_embedding(text_to_embed)
        # Deterministic ID via SHA-1 — stable across restarts (unlike Python's salted hash())
        point_id = int(hashlib.sha1(f"{guideline_id}_{rule['rule_id']}".encode()).hexdigest()[:15], 16)
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "guideline_id": guideline_id,
                    "rule_id": rule["rule_id"],
                    "section": rule["section"],
                    "rule_type": rule["rule_type"],
                    "description": rule["description"],
                    "examples_good": rule.get("examples_good", []),
                    "examples_bad": rule.get("examples_bad", []),
                },
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info("Stored %d rules in Qdrant for guideline %s", len(points), guideline_id)


def search_relevant_rules(
    query_text: str,
    guideline_id: str,
    top_k: int = 10,
) -> list[dict]:
    """Find the most relevant brand rules for a piece of content."""
    client = _get_client()
    vector = get_embedding(query_text)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        query_filter=Filter(
            must=[FieldCondition(key="guideline_id", match=MatchValue(value=guideline_id))]
        ),
        limit=top_k,
        with_payload=True,
    )
    # Filter out low-relevance results below the score threshold
    return [hit.payload for hit in results.points if hit.score >= MIN_SCORE_THRESHOLD]
