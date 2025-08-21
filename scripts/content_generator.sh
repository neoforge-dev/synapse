#!/bin/bash

# Automated Content Generation Pipeline
# Leverages Synapse RAG system for Strategic Tech Substack essays

set -euo pipefail

# Configuration
SYNAPSE_API_URL="http://localhost:8000/api/v1"
CONTENT_OUTPUT_DIR="../content/substack"
WEEKLY_CALENDAR="../SUBSTACK_CONTENT_CALENDAR_2025.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking content generation prerequisites..."
    
    # Check if Synapse API is running
    if ! curl -s "$SYNAPSE_API_URL/../../health" > /dev/null 2>&1; then
        log_error "Synapse API not running at $SYNAPSE_API_URL"
        log_info "Start with: make run-api"
        exit 1
    fi
    
    # Check required tools
    for tool in curl jq; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Create output directory
    mkdir -p "$CONTENT_OUTPUT_DIR"
    
    log_success "Prerequisites checked"
}

# Query Synapse for relevant intelligence
query_synapse() {
    local query="$1"
    local search_type="${2:-vector}"
    local top_k="${3:-10}"
    
    log_info "Querying Synapse: '$query'"
    
    curl -s -X POST "$SYNAPSE_API_URL/search/query" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"$query\",
            \"search_type\": \"$search_type\",
            \"top_k\": $top_k
        }" | jq -r '.results[].chunk.text' | head -20
}

# Extract business insights from Synapse
extract_business_insights() {
    local topic="$1"
    local week_number="$2"
    
    log_info "Extracting business insights for: $topic (Week $week_number)"
    
    # Query multiple angles for comprehensive insights
    local technical_insights
    technical_insights=$(query_synapse "$topic development practices technical implementation" "vector" 5)
    
    local business_insights  
    business_insights=$(query_synapse "$topic business impact ROI productivity automation" "vector" 5)
    
    local management_insights
    management_insights=$(query_synapse "$topic management philosophy workflow optimization" "vector" 5)
    
    # Combine insights into structured output
    cat <<EOF
# Synapse Intelligence Extraction: $topic

## Technical Implementation Insights
$technical_insights

## Business Impact Intelligence
$business_insights

## Management & Workflow Insights
$management_insights

---
*Extracted from Synapse knowledge base for Week $week_number content development*
EOF
}

# Generate essay structure based on Synapse intelligence
generate_essay_structure() {
    local week_number="$1"
    local essay_title="$2"
    local topic_keywords="$3"
    
    log_info "Generating essay structure for Week $week_number: $essay_title"
    
    # Extract relevant insights
    local synapse_insights
    synapse_insights=$(extract_business_insights "$topic_keywords" "$week_number")
    
    # Get essay date (simple calculation)
    local essay_date="2025-01-$(printf "%02d" $((7 + (week_number-1)*7)))"
    
    # Generate structured essay framework
    local title_lowercase
    title_lowercase=$(echo "$essay_title" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
    cat > "$CONTENT_OUTPUT_DIR/week_${week_number}_${title_lowercase}.md" <<EOF
# $essay_title
**Week $week_number - Strategic Tech Substack**
**Publication Date**: $essay_date
**Target Audience**: Solo founders and 2-10 person teams

---

## Synapse Intelligence Foundation

$synapse_insights

---

## Essay Framework

### Strategic Hook (200 words)
**Opening Scenario**: [Solo founder pain point related to $topic_keywords]

**Contrarian Insight**: [Unique perspective from Synapse intelligence]

**Personal Stakes**: [Quantified results and business impact]

### Core Framework: [Main Framework Name] (1000 words)

#### Component 1: [Technical Implementation] (250 words)
**Principle**: [Core technical concept]
**Synapse Intelligence**: [Relevant insight from extraction]

**Tactical Implementation**:
- [Specific CLI tools/commands]
- [Configuration examples]
- [Workflow automation]

**Business Application**: [How solo founders apply this]
**ROI Calculation**: [Specific time/cost savings]

#### Component 2: [Process Optimization] (250 words)
**Principle**: [Workflow optimization concept]
**Synapse Intelligence**: [Relevant management insight]

**Tactical Implementation**:
- [Process automation steps]
- [Integration strategies]
- [Quality assurance methods]

**Solo Founder Focus**: [Specific applications for individual contributors]
**ROI Calculation**: [Productivity measurements]

#### Component 3: [Business Integration] (250 words)
**Principle**: [Business impact concept]
**Synapse Intelligence**: [Relevant business development insight]

**Tactical Implementation**:
- [Business workflow integration]
- [Client impact strategies]
- [Revenue optimization approaches]

**Competitive Advantage**: [How this creates market differentiation]
**ROI Calculation**: [Business impact metrics]

#### Component 4: [Advanced Strategies] (250 words)
**Principle**: [Advanced implementation concept]
**Synapse Intelligence**: [Advanced insights from knowledge base]

**Tactical Implementation**:
- [Complex automation strategies]
- [Integration with other tools]
- [Scaling approaches]

**Force Multiplication**: [How this amplifies all other efforts]
**ROI Calculation**: [Compounding benefits]

### Business Impact Analysis (400 words)

#### Productivity Multiplication Metrics (200 words)
**Time Savings Quantification**:
- [Specific measurements based on Synapse insights]
- [Comparative analysis with traditional approaches]
- [Cumulative impact calculations]

**Business Value Creation**: [Revenue/cost implications]

#### Competitive Advantages Created (200 words)
**Market Differentiation**: [How this creates unique positioning]
**Client Value Delivery**: [Enhanced service capabilities]
**Operational Excellence**: [Internal efficiency gains]

### Action Framework: [Implementation Timeline] (300 words)

#### Week 1: Foundation Setup
**Daily Tasks**: [Step-by-step implementation]
**Success Metrics**: [Measurable outcomes]

#### Week 2: Integration & Optimization
**Daily Tasks**: [Advanced configuration]
**Success Metrics**: [Performance improvements]

#### Week 3-4: Scaling & Refinement
**Daily Tasks**: [Workflow optimization]
**Success Metrics**: [Business impact measurement]

### Common Pitfalls and Solutions (200 words)
**Based on Synapse Intelligence**: [Real-world challenges and solutions]

---

## Production Checklist

- [ ] Technical accuracy validation
- [ ] CLI commands tested on multiple platforms
- [ ] ROI calculations verified with real data
- [ ] Business case studies included
- [ ] Community engagement elements added
- [ ] GitHub repository examples created
- [ ] Reader feedback integration points identified

---

## Research Sources
- Synapse RAG System: $topic_keywords queries
- LinkedIn Intelligence: [Specific insights used]
- Business Development Patterns: [Management philosophy applications]

---

*Generated by Strategic Tech Content Pipeline - $(date)*
EOF

    log_success "Essay structure generated: week_${week_number}_${title_lowercase}.md"
}

# Generate weekly content batch
generate_weekly_batch() {
    local start_week="$1"
    local end_week="$2"
    
    log_info "Generating content batch: Weeks $start_week-$end_week"
    
    # Q1 Foundation Series Essays
    case $start_week in
        1) generate_essay_structure 1 "The CLI-First Productivity Revolution" "CLI productivity automation solo entrepreneur" ;;
        2) generate_essay_structure 2 "Building Your Personal AI Research Team" "AI research automation intelligence gathering" ;;
        3) generate_essay_structure 3 "From Notion to Obsidian to CLI Knowledge Management" "knowledge management CLI workflow optimization" ;;
        4) generate_essay_structure 4 "The Zero Dollar Marketing Stack" "marketing automation CLI content generation" ;;
        5) generate_essay_structure 5 "Automated Customer Research" "market research automation business intelligence" ;;
        6) generate_essay_structure 6 "The One-Person SaaS" "SaaS automation solo founder productivity" ;;
        7) generate_essay_structure 7 "Documentation That Writes Itself" "documentation automation technical writing" ;;
        8) generate_essay_structure 8 "Competitive Intelligence on Autopilot" "competitive analysis automation monitoring" ;;
        9) generate_essay_structure 9 "The Solo Founder CRM" "CRM automation relationship management" ;;
        10) generate_essay_structure 10 "Building Your Personal Bloomberg Terminal" "financial data automation analysis" ;;
        11) generate_essay_structure 11 "Email Marketing Automation" "email marketing automation campaigns" ;;
        12) generate_essay_structure 12 "The CLI-Powered Pitch Deck" "presentation automation storytelling" ;;
        13) generate_essay_structure 13 "Setting Up Your Command Center" "CLI environment setup productivity optimization" ;;
    esac
    
    log_success "Batch generation complete for weeks $start_week-$end_week"
}

# Create social media snippets from essays
generate_social_snippets() {
    local week_number="$1"
    local essay_file="$2"
    
    if [[ ! -f "$essay_file" ]]; then
        log_warning "Essay file not found: $essay_file"
        return 1
    fi
    
    log_info "Generating social media snippets for Week $week_number"
    
    # Extract key insights for social media
    local essay_title
    essay_title=$(head -1 "$essay_file" | sed 's/# //')
    
    # Query Synapse for related engagement patterns
    local engagement_insights
    engagement_insights=$(query_synapse "LinkedIn engagement controversial takes productivity" "vector" 3)
    
    # Generate LinkedIn post
    cat > "$CONTENT_OUTPUT_DIR/week_${week_number}_linkedin.md" <<EOF
# LinkedIn Post - Week $week_number

## Main Post
🚀 **$essay_title** 

[Hook from essay strategic insight]

Key insights for solo founders:
• [Tactical insight 1]
• [Tactical insight 2] 
• [Tactical insight 3]

ROI: [Specific productivity gain]

What's your biggest CLI productivity win?

#SoloFounder #CLIProductivity #TechLeadership

## Engagement Strategy
- Post Tuesday 9 AM EST
- Follow up with implementation tips in comments
- Share code examples on request
- Cross-post to Twitter with thread

## Performance Prediction
Based on Synapse engagement analysis:
- Expected reach: 2,000-5,000 impressions
- Target engagement: 50+ reactions, 10+ comments
- Conversion goal: 5-10 newsletter signups

---

## Twitter Thread
🧵 THREAD: $essay_title

1/7 [Hook tweet]

2/7 [Technical insight]

3/7 [Business impact]

4/7 [Implementation example]

5/7 [ROI calculation]

6/7 [Common mistake]

7/7 [Call to action + newsletter link]

EOF

    log_success "Social snippets generated for Week $week_number"
}

# Generate complete content package
generate_content_package() {
    local week_number="$1"
    
    log_info "🎯 Generating complete content package for Week $week_number"
    
    # Generate based on calendar
    case $week_number in
        1) 
            generate_essay_structure 1 "The CLI-First Productivity Revolution" "CLI productivity automation solo entrepreneur"
            generate_social_snippets 1 "$CONTENT_OUTPUT_DIR/week_1_the_cli-first_productivity_revolution.md"
            ;;
        2)
            generate_essay_structure 2 "Building Your Personal AI Research Team" "AI research automation intelligence gathering"  
            generate_social_snippets 2 "$CONTENT_OUTPUT_DIR/week_2_building_your_personal_ai_research_team.md"
            ;;
        3)
            generate_essay_structure 3 "From Notion to Obsidian to CLI Knowledge Management" "knowledge management CLI workflow optimization"
            generate_social_snippets 3 "$CONTENT_OUTPUT_DIR/week_3_from_notion_to_obsidian_to_cli_knowledge_management.md"
            ;;
        *)
            log_warning "Week $week_number not configured yet"
            ;;
    esac
    
    log_success "🎉 Complete content package generated for Week $week_number"
}

# Main content generation workflow  
main() {
    local command="${1:-help}"
    
    echo "📝 Strategic Tech Content Generator"
    echo "=================================="
    
    case "$command" in
        "week")
            if [[ -z "${2:-}" ]]; then
                log_error "Please specify week number: ./content_generator.sh week 1"
                exit 1
            fi
            check_prerequisites
            generate_content_package "$2"
            ;;
        "batch")
            local start_week="${2:-1}"
            local end_week="${3:-13}"
            check_prerequisites
            generate_weekly_batch "$start_week" "$end_week"
            ;;
        "query")
            if [[ -z "${2:-}" ]]; then
                log_error "Please specify query: ./content_generator.sh query 'CLI automation'"
                exit 1
            fi
            check_prerequisites
            query_synapse "$2" "${3:-vector}" "${4:-10}"
            ;;
        "insights")
            if [[ -z "${2:-}" ]]; then
                log_error "Please specify topic: ./content_generator.sh insights 'productivity automation'"
                exit 1
            fi
            check_prerequisites
            extract_business_insights "$2" "${3:-1}"
            ;;
        "help"|*)
            echo ""
            echo "Usage:"
            echo "  ./content_generator.sh week <number>     Generate complete package for specific week"  
            echo "  ./content_generator.sh batch <start> <end>   Generate batch of essays"
            echo "  ./content_generator.sh query '<keywords>'   Query Synapse for insights"
            echo "  ./content_generator.sh insights '<topic>'   Extract business insights"
            echo ""
            echo "Examples:"
            echo "  ./content_generator.sh week 1"
            echo "  ./content_generator.sh batch 1 13"  
            echo "  ./content_generator.sh query 'CLI productivity automation'"
            echo "  ./content_generator.sh insights 'workflow optimization'"
            ;;
    esac
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi