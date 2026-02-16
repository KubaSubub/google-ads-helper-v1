from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import numpy as np
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class SemanticService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            logger.info("Loading SentenceTransformer model...")
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded.")
        return cls._model

    def cluster_terms(self, terms_data: list[dict], distance_threshold=1.0):
        """
        Clusters terms using Agglomerative Clustering on embeddings.
        terms_data: list of dicts with 'text' and other metrics.
        Returns: list of clusters with aggregated metrics.
        """
        if not terms_data:
            return []

        terms = [item['text'] for item in terms_data]
        
        # Get embeddings
        model = self.get_model()
        embeddings = model.encode(terms)
        
        # Normalize embeddings for cosine similarity equivalence in Euclidean space
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Clustering
        # Ward linkage + Euclidean distance on normalized vectors works well
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric='euclidean',
            linkage='ward'
        )
        labels = clustering.fit_predict(embeddings)

        # Group by label
        clusters_map = defaultdict(list)
        for idx, label in enumerate(labels):
            clusters_map[label].append(terms_data[idx])

        # Format output
        results = []
        for label, items in clusters_map.items():
            # Aggregate metrics
            total_stats = {
                'cost': sum(i.get('cost', 0) for i in items),
                'conversions': sum(i.get('conversions', 0) for i in items),
                'clicks': sum(i.get('clicks', 0) for i in items),
                'impressions': sum(i.get('impressions', 0) for i in items),
                'term_count': len(items)
            }
            
            # Determine cluster name (term with highest impressions or cost)
            # Sorting by impressions helps find the "head" term
            best_term = sorted(items, key=lambda x: x.get('impressions', 0), reverse=True)[0]['text']

            results.append({
                'id': int(label),
                'name': best_term,
                'items': items,
                'metrics': total_stats,
                'is_waste': total_stats['cost'] > 100 and total_stats['conversions'] == 0 # Simple heuristic
            })

        # Sort clusters by Cost descending
        results.sort(key=lambda x: x['metrics']['cost'], reverse=True)
        return results
