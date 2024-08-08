import logging

import networkx as nx
import numpy as np
import pandas as pd
from langchain_core.vectorstores import VectorStore

from langchain_graphrag.types.graphs.embedding import GraphEmbeddingGenerator

logger = logging.getLogger(__name__)


class EntitiesTableGenerator:
    def __init__(
        self,
        graph_embedding_generator: GraphEmbeddingGenerator,
        entities_vector_store: VectorStore,
    ):
        self._graph_embedding_generator = graph_embedding_generator
        self._entities_vector_store = entities_vector_store

    def _unpack_nodes(
        self,
        graph: nx.Graph,
        graph_embeddings: dict[str, np.ndarray],
    ) -> pd.DataFrame:
        records = [
            {
                "title": label,
                **(node_data or {}),
                "graph_embedding": graph_embeddings.get(label),
            }
            for label, node_data in graph.nodes(data=True)
        ]
        return pd.DataFrame.from_records(records)

    def run(self, graph: nx.Graph) -> pd.DataFrame:
        # Step 1
        # Generate graph embeddings
        graph_embeddings = self._graph_embedding_generator.run(graph)

        # Step 2
        # Extract the information to embed from the graph
        # and put in the vectorstore
        texts_to_embed = []
        texts_metadata = []
        texts_ids = []
        for name, node_data in graph.nodes(data=True):
            text_description = node_data.get("description")
            texts_ids.append(node_data.get("id"))
            texts_to_embed.append(f"{name}:{text_description}")

            # Bug in langchain vectorstore retrival that
            # does not populate Document.id field.
            #
            # Hence add entity_id as an additional field
            # in the metadata
            texts_metadata.append(
                dict(
                    name=name,
                    description=text_description,
                    degree=node_data.get("degree"),
                    entity_id=node_data.get(
                        "id"
                    ),  # TODO: Remove once langchain is fixed
                )
            )

        self._entities_vector_store.add_texts(
            texts_to_embed,
            metadatas=texts_metadata,
            ids=texts_ids,
        )

        # Step 3
        # Make a dataframe
        return self._unpack_nodes(graph, graph_embeddings)
