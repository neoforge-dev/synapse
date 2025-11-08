# LinkedIn CSV Ingestion Guide for Synapse Graph-RAG

Transform your LinkedIn history into an intelligent, queryable knowledge base that preserves your beliefs, preferences, stories, and professional insights.

## What Gets Extracted

The comprehensive LinkedIn extractor processes your entire LinkedIn export to capture:

### Content Types
- **Beliefs & Opinions**: Technical philosophies, career advice, controversial takes
- **Personal Stories**: Career experiences, lessons learned, professional journey
- **Preferences**: Tool choices, methodologies, development practices
- **Ideas & Concepts**: Frameworks, approaches, strategies you've shared
- **Controversial Takes**: Unpopular opinions with engagement metrics

### Engagement Intelligence
- **High-Performing Content**: Posts with strong engagement rates
- **Business Development Signals**: Comments indicating consultation inquiries
- **Discussion Patterns**: Controversial discussions that drive engagement
- **Content Categories**: Technical, career, business, personal

### Relationship Preservation
- Entity connections (people, companies, technologies mentioned)
- Post-to-comment relationships
- Engagement patterns and metrics
- Temporal evolution of beliefs and preferences

---

## Prerequisites

### Required Files

You need to export your LinkedIn data first:

1. **LinkedIn Post Stats** (manually downloaded):
   - Location: `/Users/bogdan/data/LinkedInPost stats.csv`
   - Contains: Post content, engagement metrics, hashtags, timestamps
   - Get it from: LinkedIn Analytics > Export data

2. **Complete LinkedIn Export** (official export):
   - Location: `/Users/bogdan/data/Complete_LinkedInDataExport_XX-XX-XXXX/`
   - Request from: LinkedIn Settings > Get a copy of your data
   - Required files within export:
     - `Comments.csv` - Your comments on posts
     - `Reactions.csv` - Your reactions to content
     - `Shares.csv` - Posts you've shared with commentary

### Dependencies

All dependencies are already included in Synapse:
```bash
# Verify installation
uv run python -c "import csv, json, re; print('Ready to extract!')"
```

---

## Step-by-Step Ingestion

### Step 1: Place Your LinkedIn Export Files

Organize your LinkedIn data:

```bash
# Create data directory if it doesn't exist
mkdir -p ~/data

# Your file structure should look like:
# ~/data/
#   LinkedInPost stats.csv                          # Manual export
#   Complete_LinkedInDataExport_XX-XX-XXXX/         # Official export
#     ├── Comments.csv
#     ├── Reactions.csv
#     └── Shares.csv
```

**Expected file sizes**:
- Post stats: ~5-20 MB (for 1,000-10,000 posts)
- Comments.csv: ~2-10 MB (for 1,000-5,000 comments)
- Shares.csv: ~1-5 MB (for 500-10,000 shares)

### Step 2: Run the Comprehensive Extractor

The extractor processes all your LinkedIn data and extracts beliefs, stories, preferences, and insights:

```bash
# Navigate to your project directory
cd /Users/bogdan/til/graph-rag-mcp

# Run the comprehensive extractor
uv run python analytics/comprehensive_linkedin_extractor.py
```

**Expected output**:
```
🔍 Comprehensive LinkedIn Data Extraction
============================================================
📊 Processing 11,222+ posts, 5,222+ comments, 10,749+ shares
🎯 Extracting: beliefs, ideas, stories, preferences, controversial takes

Processing posts from /Users/bogdan/data/LinkedInPost stats.csv
Processed 1000 posts...
Processed 2000 posts...
...
Processing comments from /Users/bogdan/data/Complete_LinkedInDataExport_XX-XX-XXXX/Comments.csv
Processed 500 comments...
...
Processing shares from /Users/bogdan/data/Complete_LinkedInDataExport_XX-XX-XXXX/Shares.csv

=== Extraction Summary ===
Beliefs extracted: 487
Ideas extracted: 234
Personal stories extracted: 156
Preferences extracted: 298
Controversial takes extracted: 89

Belief categories: {'technical': 189, 'career': 142, 'business': 98, 'personal': 58}
Story categories: {'career': 78, 'technical': 45, 'business': 23, 'personal': 10}
Controversial topics: {'architecture': 34, 'technology_choice': 28, 'development_practice': 17, 'management_practice': 10}

✅ Extraction Complete!
============================================================
📊 Total items extracted: 1,264
💭 Beliefs: 487
💡 Ideas: 234
📖 Personal stories: 156
⚙️  Preferences: 298
⚡ Controversial takes: 89

📁 Dataset ready for Synapse: /Users/bogdan/til/graph-rag-mcp/data/linkedin_extracted/linkedin_comprehensive_dataset.json
🚀 Ingestion command: uv run python -m graph_rag.cli.main ingest /Users/bogdan/til/graph-rag-mcp/data/linkedin_extracted/linkedin_comprehensive_dataset.json
```

**Processing time**:
- 10,000 posts: ~2-3 minutes
- 5,000 comments: ~1 minute
- Total: ~3-5 minutes for full extraction

### Step 3: Verify Extracted Data

Check the generated files in the output directory:

```bash
# List extracted files
ls -lh data/linkedin_extracted/

# Expected files:
# linkedin_beliefs.json              (~200-500 KB)
# linkedin_ideas.json                (~150-300 KB)
# linkedin_personal_stories.json     (~100-250 KB)
# linkedin_preferences.json          (~180-350 KB)
# linkedin_controversial_takes.json  (~80-150 KB)
# linkedin_comprehensive_dataset.json (~800 KB - 2 MB)
# extraction_summary.json            (~5-10 KB)
```

Inspect the extraction summary:

```bash
# View extraction statistics
cat data/linkedin_extracted/extraction_summary.json | python -m json.tool

# Sample belief from the dataset
cat data/linkedin_extracted/linkedin_beliefs.json | python -m json.tool | head -30
```

**Example extracted belief**:
```json
{
  "id": "belief_42",
  "content": "**Belief (strong)**: microservices are often overengineered for teams under 50 developers",
  "metadata": {
    "type": "belief",
    "category": "technical",
    "confidence_level": "strong",
    "source_type": "post",
    "source_id": "post_urn:li:activity:7123456789",
    "date": "2024-03-15T09:30:00",
    "context": "After building systems at scale, I believe microservices are often overengineered for teams under 50 developers. Start with a modular monolith."
  }
}
```

### Step 4: Ingest into Synapse

Now ingest the extracted data into Synapse's knowledge graph:

```bash
# Make sure Memgraph is running (for full graph features)
make up
# OR use vector-only mode: export SYNAPSE_VECTOR_ONLY_MODE=true

# Ingest the comprehensive dataset
uv run synapse ingest data/linkedin_extracted/linkedin_comprehensive_dataset.json \
  --meta source="linkedin_export" \
  --meta extraction_date="2024-10-18"

# Alternative: Use the dedicated ingestion script
uv run python scripts/ingest_linkedin_data.py
```

**Expected output**:
```
📥 Ingesting documents...
✓ Processed: belief_0 (belief - technical)
✓ Processed: belief_1 (belief - career)
...
✓ Processed: controversial_88 (controversial_take - architecture)

📊 Ingestion Summary:
- Total items ingested: 1,264
- Beliefs: 487
- Ideas: 234
- Stories: 156
- Preferences: 298
- Controversial takes: 89
- Graph nodes created: 1,264
- Relationships created: 3,847
- Embeddings generated: 1,264

✅ LinkedIn data successfully ingested into Synapse!
```

**Processing time**: 5-10 minutes (with embeddings enabled)

### Step 5: Verify Ingestion Success

Confirm your LinkedIn data is queryable:

```bash
# Test basic search
uv run synapse search "microservices" --limit 5

# Test belief retrieval
uv run synapse search "I believe" --limit 3

# Test controversial takes
uv run synapse search "unpopular opinion" --limit 3

# Check graph statistics
uv run synapse graph stats
```

**Expected graph stats output**:
```
📊 Knowledge Graph Statistics:
- Total nodes: 1,264
- Total relationships: 3,847
- Node types: 5 (belief, idea, personal_story, preference, controversial_take)
- Average relationships per node: 3.04
- Most connected nodes:
  1. "Python development" (87 relationships)
  2. "Technical leadership" (65 relationships)
  3. "Startup scaling" (54 relationships)
```

---

## What Gets Preserved

### 1. Beliefs with Context

Every belief is preserved with:
- **Confidence level**: Strong, moderate, mild
- **Category**: Technical, career, business, personal
- **Original context**: Surrounding text for understanding
- **Engagement metrics**: How it resonated with your network
- **Temporal data**: When you expressed this belief

**Example query**:
```bash
# Find all strong technical beliefs
uv run synapse search "type:belief confidence_level:strong category:technical" --limit 10
```

### 2. Personal Stories

Your professional journey stories include:
- **Story title**: Auto-generated from content
- **Full narrative**: Complete story text
- **Lessons learned**: Extracted takeaways
- **Time period**: When it happened
- **Category classification**: Career, technical, business, personal

**Example query**:
```bash
# Find career transition stories
uv run synapse search "type:personal_story category:career" --limit 5
```

### 3. Preferences & Opinions

Your tool and methodology preferences:
- **Preference type**: Tool, methodology, approach, technology
- **Preferred option**: What you recommend
- **Reasoning**: Why you prefer it
- **Context**: Full explanation

**Example query**:
```bash
# Find Python-related preferences
uv run synapse search "type:preference Python" --limit 5
```

### 4. Controversial Takes

Your contrarian views with impact metrics:
- **Statement**: The controversial opinion
- **Controversy level**: High, medium, low (based on engagement)
- **Topic area**: Architecture, technology choice, practices, etc.
- **Reasoning**: Your supporting arguments
- **Engagement indicators**: Reactions, comments, shares

**Example query**:
```bash
# Find high-controversy architecture opinions
uv run synapse search "type:controversial_take topic_area:architecture controversy_level:high"
```

### 5. Engagement Metrics

Every piece of content preserves:
- **Reactions**: Total likes and reaction types
- **Comments**: Discussion volume
- **Shares**: Amplification metrics
- **Engagement rate**: Normalized engagement score
- **Consultation potential**: Estimated business value

---

## Querying Your LinkedIn Data

### Basic Searches

```bash
# Find all beliefs about microservices
uv run synapse search "microservices" --filter type=belief

# Find high-engagement content
uv run synapse search "engagement_rate:>0.01"

# Find recent controversial takes
uv run synapse search "type:controversial_take date:>2024-01-01"
```

### Natural Language Queries

```bash
# Ask about your technical philosophy
uv run synapse query ask "What do I believe about monoliths vs microservices?"

# Find relevant stories
uv run synapse query ask "Tell me about my career transition experiences"

# Discover patterns
uv run synapse query ask "What are my strongest technical opinions?"
```

### Graph Traversal

```bash
# Find related beliefs
uv run synapse graph neighbors "microservices" --type belief

# Explore controversial takes network
uv run synapse graph neighbors "controversial_take" --depth 2

# Find belief evolution over time
uv run synapse graph path "belief_1" "belief_50"
```

### Advanced Analytics Queries

```bash
# Find business development opportunities
uv run synapse search "consultation_potential:>=3" --limit 20

# Analyze content patterns
uv run synapse search "category:technical engagement_rate:>0.005"

# Find authenticity-driven content
uv run synapse search "authenticity_score:>0.5"
```

---

## Advanced Usage

### Custom Entity Extraction

Extract specific entities beyond the defaults:

```bash
# Run with custom patterns
uv run python analytics/comprehensive_linkedin_extractor.py --custom-patterns

# Edit the extractor to add your own patterns:
# File: analytics/comprehensive_linkedin_extractor.py
# Section: _setup_extraction_patterns()
```

**Example custom pattern** (add to the extractor):
```python
# Extract framework mentions
self.framework_patterns = [
    r"(?:using|built with|leveraging)\s+(.+?)\s+framework",
    r"(.+?)\s+is (?:the best|my preferred) framework"
]
```

### Relationship Preservation

The extractor automatically creates relationships:

- **Belief → Entity**: "belief about Python"
- **Story → Lesson**: "story teaches leadership"
- **Preference → Tool**: "prefers FastAPI over Flask"
- **Controversial Take → Topic**: "opinion on microservices"

**Query relationships**:
```bash
# Find all entities connected to a belief
uv run synapse graph neighbors "belief_42" --relationship-type MENTIONS

# Find stories that teach specific lessons
uv run synapse graph neighbors "lesson_leadership" --relationship-type TEACHES
```

### Integration with Business Development Automation

Your LinkedIn data integrates with Synapse's business development system:

```bash
# Analyze content performance patterns
uv run python analytics/linkedin_data_analyzer.py

# Generate automation insights
uv run python analytics/comprehensive_linkedin_extractor.py
cat data/linkedin_extracted/extraction_summary.json

# Use insights for content strategy
uv run python business_development/content_scheduler.py --use-linkedin-insights
```

**Business development workflow**:
1. Extract beliefs and controversial takes
2. Identify high-engagement patterns
3. Generate similar content automatically
4. Schedule posts at optimal times
5. Track consultation inquiries

---

## Troubleshooting

### File Not Found Errors

**Problem**: `FileNotFoundError: LinkedInPost stats.csv`

**Solution**:
```bash
# Verify file exists
ls -lh ~/data/LinkedInPost\ stats.csv

# Update paths in the extractor if needed
# Edit: analytics/comprehensive_linkedin_extractor.py
# Line ~808-809: Update data_dir and post_stats_file paths
```

### Encoding Issues

**Problem**: `UnicodeDecodeError` when reading CSV files

**Solution**:
```bash
# The extractor uses UTF-8 encoding by default
# If issues persist, check your CSV file encoding:
file -I ~/data/LinkedInPost\ stats.csv

# Convert to UTF-8 if needed:
iconv -f ISO-8859-1 -t UTF-8 input.csv > output.csv
```

### Missing Comments or Shares

**Problem**: `Comments.csv not found` warning

**Solution**:
```bash
# Verify LinkedIn export structure
ls -lh ~/data/Complete_LinkedInDataExport_*/

# The extractor gracefully skips missing files
# Only posts are required; comments and shares are optional
```

### Low Extraction Count

**Problem**: Only a few beliefs/stories extracted

**Possible causes**:
1. **Short posts**: Filter requires posts >100 chars
2. **Different writing style**: Patterns may not match your content
3. **Language**: Extractor optimized for English

**Solution**:
```bash
# Lower the minimum length threshold
# Edit: analytics/comprehensive_linkedin_extractor.py
# Line ~326: Change `if len(belief_text) > 10` to `> 5`

# Add custom patterns for your writing style
# See "Custom Entity Extraction" section above
```

### Ingestion Failures

**Problem**: Synapse ingestion hangs or fails

**Solution**:
```bash
# Check Memgraph is running
docker ps | grep memgraph

# Or use vector-only mode
export SYNAPSE_VECTOR_ONLY_MODE=true
uv run synapse ingest data/linkedin_extracted/linkedin_comprehensive_dataset.json

# Process in smaller batches
uv run synapse ingest data/linkedin_extracted/linkedin_beliefs.json
uv run synapse ingest data/linkedin_extracted/linkedin_ideas.json
# ... one file at a time
```

### Memory Issues

**Problem**: Extractor crashes with `MemoryError`

**Solution**:
```bash
# Process in batches (modify the extractor)
# Or increase available memory
# Or use the simpler ingestion script:
uv run python scripts/ingest_linkedin_data.py --batch-size 100
```

---

## Performance Optimization

### Fast Extraction

```bash
# Skip embeddings for faster ingestion (add later)
uv run synapse ingest data/linkedin_extracted/linkedin_comprehensive_dataset.json \
  --skip-embeddings

# Add embeddings in a separate pass
uv run synapse admin rebuild-embeddings --source linkedin_export
```

### Incremental Updates

```bash
# Export only new posts (after initial ingestion)
# Edit extraction date range in:
# analytics/comprehensive_linkedin_extractor.py

# Re-run extractor with date filter
uv run python analytics/comprehensive_linkedin_extractor.py --after 2024-10-01

# Ingest only new data
uv run synapse ingest data/linkedin_extracted/linkedin_comprehensive_dataset.json \
  --deduplicate --update-existing
```

### Query Optimization

```bash
# Create indexes for common queries
uv run synapse admin create-index --field type
uv run synapse admin create-index --field category
uv run synapse admin create-index --field engagement_rate

# Rebuild vector index for faster semantic search
uv run synapse admin rebuild-index
```

---

## What's Next?

### Enhance Your Knowledge Base

1. **Combine with other sources**:
   ```bash
   # Ingest your blog posts
   uv run synapse ingest ~/blog/posts/*.md

   # Ingest your Notion workspace
   uv run synapse notion sync --database-id YOUR_DB_ID

   # Ingest your GitHub README files
   find ~/projects -name "README.md" | xargs synapse ingest
   ```

2. **Set up automated queries**:
   ```bash
   # Daily digest of your beliefs
   echo 'synapse search "type:belief" --limit 5 --random' | crontab -e
   ```

3. **Build custom workflows**:
   ```bash
   # Create a personal knowledge assistant
   uv run synapse mcp start --port 3001
   # Connect from Claude Desktop or VS Code
   ```

### Business Development Integration

Use your LinkedIn insights to drive business:

```bash
# Generate content ideas from high-performing posts
uv run python business_development/automation_dashboard.py

# Schedule posts based on successful patterns
uv run python business_development/content_scheduler.py

# Monitor consultation inquiries
uv run python business_development/consultation_inquiry_detector.py
```

### Analytics and Insights

```bash
# Run comprehensive analytics
uv run python analytics/linkedin_data_analyzer.py

# View performance report
cat analytics/linkedin_insights_report.json | python -m json.tool | less

# Export automation-ready insights
cat analytics/linkedin_automation_data.json | python -m json.tool
```

---

## Summary

You've successfully:

1. Exported your LinkedIn data (posts, comments, shares)
2. Extracted 1,000+ beliefs, stories, preferences, and insights
3. Ingested everything into Synapse's knowledge graph
4. Made your professional history queryable and actionable

**Key Files Created**:
- `data/linkedin_extracted/linkedin_comprehensive_dataset.json` - Full dataset
- `data/linkedin_extracted/extraction_summary.json` - Statistics
- Individual category files (beliefs, ideas, stories, preferences, controversial_takes)

**Key Capabilities Unlocked**:
- Search your beliefs and opinions by topic
- Find relevant stories from your experience
- Query controversial takes and their impact
- Analyze engagement patterns
- Generate content based on successful patterns
- Drive business development from your thought leadership

**Next Steps**:
- Explore with `synapse search` and `synapse query ask`
- Integrate with business development automation
- Combine with other knowledge sources
- Set up monitoring and analytics

---

**Need Help?**

- Check extraction logs: `data/linkedin_extracted/extraction_summary.json`
- Review ingestion status: `synapse graph stats`
- Test queries: `synapse search "test"`
- Join the community: [GitHub Discussions](https://github.com/neoforge-ai/synapse-graph-rag/discussions)

Happy knowledge mining! Your LinkedIn history is now your competitive advantage.
