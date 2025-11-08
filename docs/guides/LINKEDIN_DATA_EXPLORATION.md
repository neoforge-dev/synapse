# LinkedIn Data Exploration Guide

## Overview

After ingesting your LinkedIn CSV data into Synapse, you can explore the extracted entities, relationships, and insights through multiple interfaces. This guide shows you how to query and visualize your LinkedIn knowledge graph.

## What Gets Extracted from LinkedIn CSVs

From your LinkedIn export (`LinkedInPost stats.csv` + `Comments.csv`), Synapse extracts:

### **Entities**
- **Beliefs** (strong/moderate/mild confidence levels)
- **Technical Preferences**
- **Controversial Takes** (engagement boosters)
- **Personal Stories**
- **Professional Insights**
- **Career Concepts** (leadership, mentorship, etc.)

### **Metrics**
- Engagement quality scores (weighted: comments×3 + shares×2 + reactions×1)
- Consultation potential estimation
- Viral prediction scores
- Topic performance analysis

### **Relationships**
- Post → Beliefs (HAS_BELIEF)
- Post → Topics (HAS_TOPIC)
- Comment → Insights (CONTAINS_INSIGHT)
- Belief → Topic (RELATES_TO)
- Entity → Entity (BUILDS_UPON, CONTRADICTS, INFLUENCES)

---

## Exploration Methods

### 1. Memgraph Lab (Visual Interface)

**Best for:** Visual exploration, discovering relationships, understanding graph structure

```bash
# Start Synapse stack
synapse up --wait

# Open Memgraph Lab
open http://localhost:3000
```

**What you can do:**
- Drag-and-drop graph visualization
- Cypher query editor with autocomplete
- Node/relationship property inspection
- Export visualizations as images
- Save and share query templates

**Example Queries in Memgraph Lab:**

```cypher
// Find all extracted beliefs
MATCH (b:Entity {type: 'BELIEF'})
RETURN b.name, b.confidence, b.text
LIMIT 20;

// Get posts with highest engagement
MATCH (p:Document)
WHERE p.metadata.engagement_score IS NOT NULL
RETURN p.metadata.title,
       p.metadata.engagement_score,
       p.metadata.consultation_potential
ORDER BY p.metadata.engagement_score DESC
LIMIT 10;

// Find controversial takes with high engagement
MATCH (c:Entity {type: 'HOT_TAKE'})
RETURN c.name, c.engagement_potential, c.text
ORDER BY c.engagement_potential DESC;

// Explore belief relationships
MATCH (b1:Entity {type: 'BELIEF'})-[r]->(b2:Entity {type: 'BELIEF'})
RETURN b1.name, type(r), b2.name
LIMIT 20;

// Find posts about specific topics
MATCH (p:Document)-[:HAS_TOPIC]->(t:Entity {type: 'Topic'})
WHERE t.name = 'AI' OR t.name = 'machine learning'
RETURN p.metadata.title, p.content
LIMIT 10;

// Get technical preferences
MATCH (tp:Entity {type: 'TECHNICAL_PREFERENCE'})
RETURN tp.name, tp.preference_type, tp.confidence
ORDER BY tp.confidence DESC;

// Find engagement winners (>1% engagement rate)
MATCH (p:Document)
WHERE p.metadata.engagement_rate > 0.01
RETURN p.metadata.title,
       p.metadata.engagement_rate,
       p.metadata.numReactions,
       p.metadata.numComments,
       p.metadata.numShares
ORDER BY p.metadata.engagement_rate DESC;

// Discover belief clusters
MATCH (b:Entity {type: 'BELIEF'})-[:RELATES_TO]->(t:Entity {type: 'Topic'})
RETURN t.name AS topic,
       count(b) AS belief_count,
       collect(b.name)[..5] AS sample_beliefs
ORDER BY belief_count DESC;

// Find comment insights
MATCH (c:Document {type: 'Comment'})-[:CONTAINS_INSIGHT]->(i:Entity)
RETURN c.content, i.type, i.name
LIMIT 20;
```

---

### 2. Synapse CLI (Command Line)

**Best for:** Scripting, batch operations, quick queries

#### Basic Search

```bash
# Search for beliefs
synapse search "I believe" --type keyword --limit 20

# Find controversial content
synapse search "controversial" --type vector --limit 10

# Search with explanations
synapse explain explain "technical preferences" --entities --relations
```

#### Graph Exploration Commands

```bash
# Get neighbors of a specific entity
synapse graph neighbors --id "BELIEF:technical_leadership" --depth 2 --json

# Export subgraph around a belief
synapse graph export \
  --seed "BELIEF:ai_transforms_business" \
  --depth 2 \
  --format graphml \
  --out linkedin_beliefs_subgraph.xml

# Visualize in browser (opens interactive visualization)
synapse graph viz --seed "Topic:AI"
```

#### Query with Q&A

```bash
# Ask questions about your beliefs
synapse query ask "What are my core beliefs about AI and machine learning?" \
  --show-chunks --show-graph

# Find controversial takes
synapse query ask "What controversial opinions do I have?" \
  --k 10 --show-citations

# Explore technical preferences
synapse query ask "What are my technical preferences and why?" \
  --search-type hybrid
```

---

### 3. REST API (Programmatic Access)

**Best for:** Integrations, dashboards, custom applications

#### Graph Visualization API

```bash
# Get graph visualization data for beliefs
curl "http://localhost:8000/api/v1/advanced-features/graph/visualize?query=beliefs&max_nodes=50" | jq .

# Get comprehensive graph statistics
curl "http://localhost:8000/api/v1/advanced-features/graph/stats" | jq .
```

**Example Response (Graph Stats):**
```json
{
  "total_nodes": 1247,
  "total_relationships": 3891,
  "node_types": {
    "Document": 460,
    "Chunk": 2341,
    "Entity": 446
  },
  "relationship_types": {
    "CONTAINS": 2341,
    "MENTIONS": 1328,
    "HAS_TOPIC": 122,
    "BUILDS_UPON": 43,
    "CONTRADICTS": 12
  },
  "graph_density": 0.0051,
  "connected_components": 1
}
```

#### Graph Analysis API

```bash
# Analyze beliefs and their relationships
curl -X POST "http://localhost:8000/api/v1/advanced-features/graph/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "beliefs about AI",
    "depth": 2,
    "include_entities": true,
    "include_relationships": true
  }' | jq .
```

#### Search API

```bash
# Vector search for controversial takes
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "controversial opinion unpopular take",
    "search_type": "vector",
    "limit": 10
  }' | jq .

# Query with answer synthesis
curl -X POST "http://localhost:8000/api/v1/query/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are my most controversial beliefs?",
    "search_type": "hybrid",
    "limit": 10,
    "include_citations": true
  }' | jq .
```

---

## Specific Exploration Scenarios

### Scenario 1: Find Your Unique Beliefs

**Cypher Query (Memgraph Lab):**
```cypher
MATCH (b:Entity {type: 'BELIEF'})
WHERE b.confidence IN ['strong', 'moderate']
RETURN b.name, b.text, b.confidence, b.context_window
ORDER BY b.confidence DESC, b.name
LIMIT 20;
```

**CLI:**
```bash
synapse search "I believe" --type keyword | jq '.results[].chunk.text'
```

**API:**
```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "belief conviction opinion", "search_type": "vector", "limit": 20}' \
  | jq '.results[] | {text: .chunk.text, score: .score}'
```

---

### Scenario 2: Analyze Technical Preferences

**Cypher:**
```cypher
MATCH (tp:Entity {type: 'TECHNICAL_PREFERENCE'})
RETURN tp.name,
       tp.preference_type,
       tp.confidence,
       tp.context_window
ORDER BY tp.confidence DESC;
```

**CLI:**
```bash
synapse query ask "What are my technical preferences? Compare and contrast them." \
  --show-chunks --k 15
```

---

### Scenario 3: Find Engagement Winners

**Cypher:**
```cypher
MATCH (p:Document)
WHERE p.metadata.engagement_rate > 0.01
  AND p.metadata.numComments >= 5
RETURN p.metadata.title,
       p.metadata.engagement_rate,
       p.metadata.numReactions,
       p.metadata.numComments,
       p.metadata.numShares,
       p.metadata.consultation_potential,
       p.content[..200] + '...' AS preview
ORDER BY p.metadata.engagement_rate DESC
LIMIT 20;
```

**CLI:**
```bash
# Search for high-engagement posts
synapse search "engagement" --type keyword --limit 50 \
  | jq '.results[] | select(.document.metadata.engagement_rate > 0.01)'
```

---

### Scenario 4: Discover Controversial Takes

**Cypher:**
```cypher
MATCH (ht:Entity {type: 'HOT_TAKE'})
OPTIONAL MATCH (ht)<-[:MENTIONS]-(c:Chunk)<-[:CONTAINS]-(p:Document)
RETURN ht.name,
       ht.text,
       ht.engagement_potential,
       p.metadata.engagement_rate,
       p.metadata.numComments
ORDER BY ht.engagement_potential DESC
LIMIT 15;
```

**API (with viral prediction):**
```bash
curl -X POST "http://localhost:8000/api/v1/advanced-features/hot-takes/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Unpopular opinion: Most AI tools are overhyped",
    "platform": "linkedin",
    "analysis_depth": "comprehensive"
  }' | jq .
```

---

### Scenario 5: Explore Relationship Networks

**Cypher:**
```cypher
// Find beliefs that build upon each other
MATCH (b1:Entity {type: 'BELIEF'})-[r:BUILDS_UPON]->(b2:Entity {type: 'BELIEF'})
RETURN b1.name AS from_belief,
       b2.name AS to_belief,
       r.confidence AS relationship_confidence,
       r.evidence_text AS evidence
ORDER BY r.confidence DESC;

// Find contradicting beliefs
MATCH (b1:Entity)-[r:CONTRADICTS]->(b2:Entity)
RETURN b1.name AS belief1,
       b2.name AS belief2,
       r.evidence_text AS conflict_evidence;
```

**Graph Visualization:**
```bash
# Export relationship network for visualization
synapse graph export \
  --seed "BELIEF:ai_transforms_business" \
  --depth 3 \
  --format graphml \
  --out belief_network.graphml

# Import into Gephi, Cytoscape, or yEd for advanced visualization
```

---

### Scenario 6: Track Metrics Over Time

**Cypher:**
```cypher
MATCH (p:Document)
WHERE p.metadata.createdAt IS NOT NULL
RETURN date(p.metadata.createdAt) AS post_date,
       avg(p.metadata.engagement_rate) AS avg_engagement,
       sum(p.metadata.numComments) AS total_comments,
       count(p) AS post_count
ORDER BY post_date DESC
LIMIT 52;  // Last 52 weeks
```

---

## Advanced Exploration

### Python Script for Custom Analysis

```python
#!/usr/bin/env python3
"""
Custom LinkedIn data analysis using Synapse API
"""
import httpx
import pandas as pd

API_BASE = "http://localhost:8000/api/v1"

def get_all_beliefs():
    """Extract all beliefs from graph."""
    response = httpx.post(
        f"{API_BASE}/search",
        json={
            "query": "belief conviction opinion",
            "search_type": "vector",
            "limit": 100
        }
    )
    return response.json()

def analyze_engagement_patterns():
    """Analyze which belief types drive most engagement."""
    beliefs = get_all_beliefs()

    df = pd.DataFrame([
        {
            "text": r["chunk"]["text"],
            "engagement": r["document"]["metadata"].get("engagement_rate", 0),
            "comments": r["document"]["metadata"].get("numComments", 0),
            "score": r["score"]
        }
        for r in beliefs["results"]
    ])

    print("\nTop 10 High-Engagement Beliefs:")
    print(df.nlargest(10, "engagement")[["text", "engagement", "comments"]])

    print("\nEngagement Statistics:")
    print(df[["engagement", "comments"]].describe())

if __name__ == "__main__":
    analyze_engagement_patterns()
```

**Run:**
```bash
python scripts/analyze_linkedin_beliefs.py
```

---

## Visualization Options

### 1. **Memgraph Lab** (Built-in)
- URL: http://localhost:3000
- Features: Interactive graph, query builder, export images

### 2. **Export to External Tools**

```bash
# Export to GraphML for Gephi/Cytoscape
synapse graph export --format graphml --out linkedin_graph.graphml

# Export to JSON for D3.js/vis.js
synapse graph export --format json --out linkedin_graph.json
```

**Recommended External Tools:**
- **Gephi**: Network analysis and visualization
- **Cytoscape**: Biological networks (works for any graph)
- **yEd**: Automatic layout algorithms
- **Neo4j Bloom**: Visual graph exploration (if you migrate to Neo4j)

### 3. **Custom Web Dashboard**

Create a simple dashboard using the visualization API:

```html
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn Beliefs Explorer</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
</head>
<body>
    <div id="network" style="width: 100%; height: 800px;"></div>
    <script>
        fetch('http://localhost:8000/api/v1/advanced-features/graph/visualize?query=beliefs&max_nodes=50')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('network');
                const options = {
                    nodes: { shape: 'dot', size: 20 },
                    edges: { arrows: 'to' }
                };
                new vis.Network(container, data, options);
            });
    </script>
</body>
</html>
```

---

## Common Queries Reference

### Find Specific Content

```cypher
// All posts about AI
MATCH (p:Document)-[:HAS_TOPIC]->(t:Entity {name: 'AI'})
RETURN p;

// Beliefs with high confidence
MATCH (b:Entity {type: 'BELIEF'})
WHERE b.confidence = 'strong'
RETURN b;

// Posts with consultation potential
MATCH (p:Document)
WHERE p.metadata.consultation_potential >= 3
RETURN p
ORDER BY p.metadata.consultation_potential DESC;
```

### Aggregate Statistics

```cypher
// Count entities by type
MATCH (e:Entity)
RETURN e.type, count(e) AS count
ORDER BY count DESC;

// Average engagement by topic
MATCH (p:Document)-[:HAS_TOPIC]->(t:Entity {type: 'Topic'})
RETURN t.name AS topic,
       avg(p.metadata.engagement_rate) AS avg_engagement,
       count(p) AS post_count
ORDER BY avg_engagement DESC;

// Consultation conversion rate
MATCH (p:Document)
RETURN avg(p.metadata.consultation_potential) AS avg_potential,
       count(CASE WHEN p.metadata.consultation_potential >= 3 THEN 1 END) AS high_potential_count,
       count(p) AS total_posts;
```

---

## Troubleshooting

### Graph appears empty
```bash
# Check if data was ingested
synapse admin vector-stats

# Verify Memgraph connection
curl http://localhost:7687
```

### Slow queries
```cypher
// Add index on frequently queried properties
CREATE INDEX ON :Entity(type);
CREATE INDEX ON :Document(engagement_rate);
```

### Cannot see specific entities
```bash
# Re-run entity extraction
python analytics/comprehensive_linkedin_extractor.py

# Re-ingest
synapse ingest data/linkedin_extracted/ --embeddings --replace
```

---

## Next Steps

1. **Explore with Memgraph Lab**: Start with visual exploration
2. **Run example queries**: Copy-paste Cypher queries above
3. **Export for analysis**: Use GraphML export for Gephi
4. **Build dashboards**: Use visualization API for custom UIs
5. **Automate insights**: Create Python scripts for recurring analysis

---

## Related Documentation

- [LinkedIn Data Ingestion](./LINKEDIN_DATA_INGESTION.md)
- [Graph Query Reference](./GRAPH_QUERY_REFERENCE.md)
- [API Documentation](../reference/API_REFERENCE.md)
- [Cypher Query Language](https://memgraph.com/docs/cypher-manual)
