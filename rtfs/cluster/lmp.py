import json
from typing import List, Dict

def create_2tier_hierarchy(
    model: LLMModel, 
    clusters: List[Cluster],
    existing_parents: Dict[str, List[str]] = None
) -> List[ParentCluster]:
    cluster_text = "\n".join([
        f"Cluster {c.id}: {c.summary.title} - {c.summary.summary}"
        for c in clusters
    ])
    
    existing_categories = ""
    if existing_parents and len(existing_parents) > 0:
        existing_categories = "Existing categories:\n" + "\n".join([
            f"- {name}: {', '.join(child_ids)}"
            for name, child_ids in existing_parents.items()
        ])
        
    prompt = f"""Group these code clusters into 2-4 high-level categories based on their functionality and purpose.
{existing_categories}

Clusters to organize:
{cluster_text}

Rules:
1. Each cluster must be assigned to exactly one category
2. You can assign clusters to existing categories if they fit
3. Create new categories only if needed
4. Category names should be descriptive of the grouped clusters' purpose

Return the assignments in this JSON format:
{{
    "categories": [
        {{
            "name": "Category name (new or existing)",
            "child_names": ["cluster1_id", "cluster2_id", ...]
        }},
        ...
    ]
}}
"""
    response = model.complete(prompt)
    result = json.loads(response)
    return [ParentCluster(**category) for category in result["categories"]]