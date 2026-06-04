from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.server.storing.schemas import DeleteRequest, EditRequest, StoreRequest
from ragrails.interfaces.server.storing.services import delete_chunks, edit_chunks, store_chunks
from ragrails.interfaces.sdk import RagRails
from ragrails.types import DeleteResult, EditResult, StoreResult


class ServerStoringServiceTests(unittest.TestCase):
    def test_store_calls_sdk(self) -> None:
        expected = StoreResult(inputs=1, stored=1, items=[{"id": "chunk-1"}], failed=0, provider="qdrant", collection="docs", errors=[])

        with patch.object(RagRails, "store", return_value=expected) as store:
            result = store_chunks(StoreRequest(embedded_chunks=[{"id": "chunk-1", "embedding": [1.0]}], collection="docs"))

        store.assert_called_once()
        self.assertEqual(store.call_args.kwargs["embedded_chunks"], [{"id": "chunk-1", "embedding": [1.0]}])
        self.assertEqual(result["stored"], 1)

    def test_edit_creates_embedder_and_calls_sdk(self) -> None:
        expected = EditResult(requested=1, edited=1, items=[{"id": "chunk-1"}], failed=0, provider="qdrant", collection="docs", errors=[])
        fake_embedder = object()

        with (
            patch.object(RagRails, "embedder", return_value=fake_embedder) as embedder,
            patch.object(RagRails, "edit", return_value=expected) as edit,
        ):
            result = edit_chunks(EditRequest(chunks=[{"id": "chunk-1", "text": "updated"}], collection="docs"))

        embedder.assert_called_once_with(provider="voyage", model="voyage-3", input_type="document", options=None)
        edit.assert_called_once()
        self.assertIs(edit.call_args.kwargs["embedder"], fake_embedder)
        self.assertEqual(result["edited"], 1)

    def test_delete_calls_sdk(self) -> None:
        expected = DeleteResult(requested=1, deleted=1, items=[{"id": "chunk-1"}], failed=0, provider="qdrant", collection="docs", errors=[])

        with patch.object(RagRails, "delete", return_value=expected) as delete:
            result = delete_chunks(DeleteRequest(ids=["chunk-1"], collection="docs"))

        delete.assert_called_once_with(ids=["chunk-1"], vector_db="qdrant", collection="docs", url=None, options=None)
        self.assertEqual(result["deleted"], 1)


if __name__ == "__main__":
    unittest.main()
