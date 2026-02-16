import sys
import os
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.semantic import SemanticService

def test_clustering():
    print("Initializing SemanticService...")
    service = SemanticService()
    
    terms = [
        {'text': 'tanie meble', 'cost': 10, 'clicks': 100},
        {'text': 'meble do salonu', 'cost': 20, 'clicks': 50},
        {'text': 'sofa rozkładana', 'cost': 50, 'clicks': 20},
        {'text': 'kanapa z funkcją spania', 'cost': 40, 'clicks': 25},
        {'text': 'iphone 15 case', 'cost': 5, 'clicks': 10},
        {'text': 'etui na iphone', 'cost': 6, 'clicks': 12},
    ]
    
    print("Clustering terms...")
    try:
        clusters = service.cluster_terms(terms, distance_threshold=1.5)
        print(f"Found {len(clusters)} clusters.")
        for c in clusters:
            print(f"Cluster: {c['name']} (Count: {c['metrics']['term_count']})")
            for item in c['items']:
                print(f" - {item['text']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_clustering()
