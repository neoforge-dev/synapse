# LinkedIn CSV Ingestion - Quick Start Guide

## Overview

This guide shows you how to ingest your LinkedIn export data into Synapse and explore the extracted knowledge graph in **under 10 minutes**.

## Prerequisites

```bash
# Ensure Synapse is installed and configured
synapse --version

# Start the graph database
synapse up --wait
```

## Step 1: Locate Your LinkedIn Export

LinkedIn provides CSV exports with your post history:

```
/Users/bogdan/data/
├── LinkedInPost stats.csv               # Your posts with engagement metrics
└── Complete_LinkedInDataExport_XX-XX-XXXX/
    ├── Comments.csv                     # Your comments on posts
    ├── Reactions.csv                    # Your reactions
    └── Shares.csv                       # Content you shared
```

## Step 2: Extract Intelligence from CSV

You have **4 ready-to-use extraction scripts**:

### Option A: Comprehensive Extraction (Recommended)

```bash
cd /Users/bogdan/til/graph-rag-mcp

# Run comprehensive extractor
python analytics/comprehensive_linkedin_extractor.py

# This creates:
# - data/linkedin_extracted/linkedin_comprehensive_dataset.json
# - data/linkedin_extracted/linkedin_beliefs.json
# - data/linkedin_extracted/linkedin_ideas.json
# - data/linkedin_extracted/linkedin_personal_stories.json
# - data/linkedin_extracted/linkedin_preferences.json
# - data/linkedin_extracted/linkedin_controversial_takes.json
```

**What it extracts:**
- ✅ **179 unique beliefs** (strong/moderate/mild confidence)
- ✅ **314 engagement winners** (>1% engagement rate)
- ✅ **26 controversial takes** (high viral potential)
- ✅ **18 technical preferences**
- ✅ **Complete engagement metrics** per post

### Option B: Focused Content Extraction

```bash
# Extract specific patterns (beliefs, preferences, stories)
python scripts/ingest_linkedin_content.py

# Outputs to: data/linkedin_processed/
```

### Option C: Business Intelligence Analysis

```bash
# Extract with consultation potential scoring
python analytics/linkedin_data_analyzer.py

# Calculates:
# - Engagement quality scores
# - Consultation potential per post
# - Topic performance analysis
# - Business inquiry detection
```

## Step 3: Ingest into Synapse

```bash
# Ingest all extracted data with embeddings
synapse ingest data/linkedin_extracted/ \
  --embeddings \
  --include "*.json" \
  --batch-size 50

# Expected output:
# ✓ Ingested 460 documents
# ✓ Created 2,341 chunks
# ✓ Extracted 446 entities
# ✓ Generated 3,891 relationships
```

**Processing Time**: ~5-10 minutes (depending on dataset size)

## Step 4: Verify Ingestion

```bash
# Check vector store stats
synapse admin vector-stats

# Expected output:
# Total vectors: 2,341
# Embedding dimension: 384
# Index type: faiss
```

```bash
# Quick search test
synapse search "beliefs about AI" --limit 5

# Should return relevant chunks with scores
```

## Step 5: Explore Your Data

### 5.1 Visual Exploration (Memgraph Lab)

```bash
# Open Memgraph Lab in browser
open http://localhost:3000
```

**Run these queries:**

```cypher
// View all extracted beliefs
MATCH (b:Entity {type: 'BELIEF'})
RETURN b.name, b.confidence, b.text
LIMIT 20;

// Find engagement winners
MATCH (p:Document)
WHERE p.metadata.engagement_rate > 0.01
RETURN p.metadata.title, p.metadata.engagement_rate
ORDER BY p.metadata.engagement_rate DESC
LIMIT 10;

// Explore controversial takes
MATCH (c:Entity {type: 'HOT_TAKE'})
RETURN c.name, c.engagement_potential
ORDER BY c.engagement_potential DESC;
```

### 5.2 CLI Exploration

```bash
# Ask questions about your beliefs
synapse query ask "What are my core beliefs about AI and machine learning?" \
  --show-chunks --show-graph

# Find technical preferences
synapse query ask "What are my technical preferences?" --k 10

# Discover controversial opinions
synapse search "unpopular opinion controversial take" --type vector --limit 10
```

### 5.3 Graph Visualization

```bash
# Export graph for visualization
synapse graph export \
  --seed "BELIEF:ai_transforms_business" \
  --depth 2 \
  --format graphml \
  --out linkedin_beliefs.graphml

# Import into Gephi or Cytoscape for advanced visualization
```

### 5.4 API Access

```bash
# Get graph statistics
curl "http://localhost:8000/api/v1/advanced-features/graph/stats" | jq .

# Visualize beliefs network
curl "http://localhost:8000/api/v1/advanced-features/graph/visualize?query=beliefs&max_nodes=50" | jq .

# Search for controversial content
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "controversial opinion",
    "search_type": "vector",
    "limit": 10
  }' | jq .
```

## What You Get

### Entities Extracted

1. **Beliefs** (`type: BELIEF`)
   - Strong: "I believe that AI will transform..."
   - Moderate: "I think that microservices..."
   - Mild: "It seems that distributed systems..."

2. **Technical Preferences** (`type: TECHNICAL_PREFERENCE`)
   - "I prefer TypeScript over JavaScript"
   - "GraphRAG is superior to naive RAG"

3. **Controversial Takes** (`type: HOT_TAKE`)
   - "Unpopular opinion: Most AI tools are overhyped"
   - "Hot take: Monoliths beat microservices for 80% of startups"

4. **Professional Insights** (`type: INSIGHT`)
   - "Key lesson: Scale teams before scaling systems"
   - "Takeaway: Technical debt compounds faster than financial debt"

5. **Personal Stories** (`type: PERSONAL_STORY`)
   - Anecdotes, experiences, case studies

### Relationships Created

```
Document -[:CONTAINS]-> Chunk
Chunk -[:MENTIONS]-> Entity
Document -[:HAS_TOPIC]-> Topic
Belief -[:BUILDS_UPON]-> Belief
Belief -[:CONTRADICTS]-> Belief
Concept -[:INFLUENCES]-> Concept
```

### Metrics Available

- **Engagement Rate**: (comments×3 + shares×2 + reactions×1) / views
- **Consultation Potential**: Likelihood of driving business inquiries (0-5 scale)
- **Viral Score**: Predicted engagement based on content analysis
- **Controversy Score**: Presence of polarizing elements
- **Confidence Levels**: Entity extraction confidence (0.0-1.0)

## Common Queries

### Find Your Most Engaging Content

```cypher
MATCH (p:Document)
WHERE p.metadata.engagement_rate IS NOT NULL
RETURN p.metadata.title,
       p.metadata.engagement_rate,
       p.metadata.numComments,
       p.metadata.numShares,
       p.content[..200] + '...' AS preview
ORDER BY p.metadata.engagement_rate DESC
LIMIT 10;
```

### Discover Belief Clusters

```cypher
MATCH (b:Entity {type: 'BELIEF'})-[:RELATES_TO]->(t:Entity {type: 'Topic'})
RETURN t.name AS topic,
       count(b) AS belief_count,
       collect(b.name)[..5] AS sample_beliefs
ORDER BY belief_count DESC;
```

### Analyze What Drives Consultation Inquiries

```cypher
MATCH (p:Document)
WHERE p.metadata.consultation_potential >= 3
RETURN p.metadata.title,
       p.metadata.consultation_potential,
       p.metadata.engagement_rate,
       p.metadata.topics AS topics
ORDER BY p.metadata.consultation_potential DESC
LIMIT 15;
```

## Troubleshooting

### No results from search

```bash
# Verify ingestion
synapse admin vector-stats

# Check Memgraph connection
docker ps | grep memgraph

# Re-ingest if needed
synapse ingest data/linkedin_extracted/ --embeddings --replace
```

### Slow queries

```cypher
// Add indexes in Memgraph Lab
CREATE INDEX ON :Entity(type);
CREATE INDEX ON :Document(engagement_rate);
```

### Missing entities

```bash
# Re-run extraction
python analytics/comprehensive_linkedin_extractor.py

# Re-ingest
synapse ingest data/linkedin_extracted/linkedin_comprehensive_dataset.json \
  --embeddings --replace
```

## Next Steps

1. ✅ **Explore beliefs**: `synapse query ask "What are my unique beliefs?"`
2. ✅ **Find patterns**: Use Memgraph Lab for visual exploration
3. ✅ **Build dashboards**: Use `/graph/visualize` API endpoint
4. ✅ **Analyze engagement**: Compare high vs low engagement content
5. ✅ **Extract insights**: Run custom Cypher queries

## Related Documentation

- [Complete LinkedIn Data Exploration Guide](./LINKEDIN_DATA_EXPLORATION.md)
- [Graph Query Reference](./GRAPH_QUERY_REFERENCE.md)
- [Memgraph vs FalkorDB Evaluation](../analysis/MEMGRAPH_VS_FALKORDB_EVALUATION.md)
- [API Documentation](../reference/API_REFERENCE.md)

---

**Estimated Time**: 10 minutes from CSV to explorable knowledge graph
**Difficulty**: Easy (all scripts ready to use)
**Prerequisites**: Synapse installed, LinkedIn CSV export downloaded
