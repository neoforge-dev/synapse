#!/bin/bash

# Gemini CLI Validator - Market validation and gap analysis tool
# Requires GEMINI_API_KEY environment variable

set -euo pipefail

# Configuration
GEMINI_API_KEY=${GEMINI_API_KEY:-""}
GEMINI_API_URL="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
ANALYSIS_DATE=$(date +%Y%m%d_%H%M)
RESULTS_DIR="gemini_analysis_$ANALYSIS_DATE"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if [[ -z "$GEMINI_API_KEY" ]]; then
        log_error "GEMINI_API_KEY environment variable not set"
        echo "Please set your Gemini API key: export GEMINI_API_KEY=your_key_here"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed"
        exit 1
    fi
    
    log_success "Prerequisites checked"
}

# Validate with Gemini API
validate_with_gemini() {
    local analysis_type="$1"
    local context_file="$2"
    local output_file="$3"
    
    log_info "Running Gemini validation: $analysis_type"
    
    if [[ ! -f "$context_file" ]]; then
        log_error "Context file not found: $context_file"
        return 1
    fi
    
    # Prepare context and prompt
    local context
    context=$(cat "$context_file")
    local prompt
    prompt=$(generate_validation_prompt "$analysis_type" "$context")
    
    # Create JSON payload with proper escaping
    local json_payload
    json_payload=$(jq -n \
        --arg prompt "$prompt" \
        '{
            "contents": [{
                "parts": [{
                    "text": $prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192
            }
        }')
    
    # Query Gemini API
    local response
    response=$(curl -s -X POST "$GEMINI_API_URL?key=$GEMINI_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$json_payload")
    
    # Check for API errors
    if echo "$response" | jq -e '.error' > /dev/null; then
        log_error "Gemini API error: $(echo "$response" | jq -r '.error.message')"
        return 1
    fi
    
    # Extract and save response
    echo "$response" | jq -r '.candidates[0].content.parts[0].text' > "$output_file"
    
    log_success "Analysis complete: $output_file"
}

# Generate validation prompts based on type
generate_validation_prompt() {
    local analysis_type="$1"
    local context="$2"
    
    case "$analysis_type" in
        "market_opportunity")
            generate_market_validation_prompt "$context"
            ;;
        "competitive_intelligence") 
            generate_competitive_prompt "$context"
            ;;
        "content_gaps")
            generate_content_gap_prompt "$context"
            ;;
        "business_model")
            generate_business_model_prompt "$context"
            ;;
        *)
            log_error "Unknown analysis type: $analysis_type"
            exit 1
            ;;
    esac
}

# Market validation prompt
generate_market_validation_prompt() {
    local context="$1"
    
    cat <<EOF
You are a market research expert analyzing a content strategy for solo founders and small teams.

CONTEXT:
$context

ANALYSIS REQUEST:
1. Market Size Assessment:
   - Estimate the addressable market for CLI productivity tools for solo founders
   - Compare market size vs traditional productivity/SaaS markets
   - Identify market growth trends and drivers

2. Competition Analysis:
   - Map existing competitors in this space
   - Identify content gaps not being served
   - Assess barriers to entry and competitive advantages

3. Market Timing:
   - Is this the right time for CLI-first productivity content?
   - What external factors support/hinder adoption?
   - Predict market evolution over next 2-3 years

4. Target Audience Validation:
   - Validate solo founder + small team focus
   - Identify potential audience expansion opportunities
   - Assess audience pain points and willingness to pay

5. Content Strategy Assessment:
   - Evaluate the 52-essay calendar approach
   - Identify potential content gaps or redundancies
   - Suggest optimization opportunities

FORMAT: Structured analysis with specific recommendations and quantifiable insights where possible. Include confidence levels for major assertions.
EOF
}

# Competitive analysis prompt
generate_competitive_prompt() {
    local context="$1"
    
    cat <<EOF
You are a competitive intelligence analyst evaluating a content strategy position.

CONTEXT:
$context

COMPETITIVE ANALYSIS REQUEST:
1. Direct Competitors:
   - Identify newsletters/content targeting similar audiences
   - Analyze their positioning, pricing, and content approach
   - Map their strengths and weaknesses

2. Indirect Competitors:
   - General productivity content creators
   - Technical tutorial platforms
   - Business development content
   - AI/automation focused content

3. Competitive Advantages Assessment:
   - Evaluate uniqueness of CLI-first approach
   - Assess sustainability of competitive moats
   - Identify potential commoditization risks

4. Pricing Strategy:
   - Research comparable content pricing models
   - Assess price sensitivity for target audience
   - Recommend pricing strategy and tiers

5. Distribution Strategy:
   - Analyze competitor distribution channels
   - Identify underutilized channels for this content
   - Recommend multi-channel strategy

6. Partnership Opportunities:
   - Identify potential collaboration targets
   - Assess partnership models in this space
   - Recommend strategic alliances

FOCUS: Actionable competitive intelligence with specific strategic recommendations and competitor analysis.
EOF
}

# Content gap analysis prompt
generate_content_gap_prompt() {
    local context="$1"
    
    cat <<EOF
You are a content strategy consultant analyzing an editorial calendar for blind spots and opportunities.

CONTEXT:
$context

GAP ANALYSIS REQUEST:
1. Content Coverage Assessment:
   - Identify topics missing from the 52-essay calendar
   - Spot potential redundancies or overlaps
   - Assess topic progression and learning curve

2. Audience Journey Mapping:
   - Map content to customer journey stages
   - Identify gaps in onboarding, engagement, retention
   - Recommend content for each funnel stage

3. Technical Depth Analysis:
   - Assess balance between beginner and advanced content
   - Identify areas needing more/less technical detail
   - Recommend skill-level progression strategy

4. Business Impact Focus:
   - Evaluate ROI demonstration across content
   - Identify missing business case studies
   - Recommend metrics and measurement content

5. Community Building Elements:
   - Assess content for community engagement potential
   - Identify opportunities for user-generated content
   - Recommend interactive and collaborative elements

6. Emerging Technology Integration:
   - Identify cutting-edge CLI tools not covered
   - Assess future-proofing of content strategy
   - Recommend technology trend integration

7. Monetization Alignment:
   - Map content to revenue generation opportunities
   - Identify premium content candidates
   - Recommend upsell and cross-sell integration

OUTPUT: Prioritized list of content gaps with specific essay topics and business justification.
EOF
}

# Business model validation prompt
generate_business_model_prompt() {
    local context="$1"
    
    cat <<EOF
You are a business model strategist analyzing a content-driven business approach.

CONTEXT:
$context

BUSINESS MODEL ANALYSIS:
1. Revenue Model Assessment:
   - Evaluate newsletter → consulting funnel effectiveness
   - Assess scalability of current revenue streams
   - Identify additional monetization opportunities

2. Customer Acquisition Analysis:
   - Evaluate organic content marketing approach
   - Assess customer acquisition costs and LTV
   - Recommend paid acquisition strategies

3. Product-Market Fit Indicators:
   - Identify PMF signals to track
   - Recommend validation experiments
   - Define success metrics and benchmarks

4. Operational Scalability:
   - Assess content production sustainability
   - Identify automation and delegation opportunities
   - Recommend team scaling approach

5. Financial Projections:
   - Estimate revenue potential by year 2-3
   - Model different growth scenarios
   - Identify key financial drivers and risks

6. Strategic Partnerships:
   - Identify revenue-generating partnerships
   - Assess platform and tool integration opportunities
   - Recommend affiliate and referral strategies

7. Exit Strategy Options:
   - Evaluate long-term exit possibilities
   - Assess business asset value creation
   - Recommend strategic positioning for exits

FOCUS: Quantitative analysis with specific financial projections and strategic recommendations.
EOF
}

# Generate summary report
generate_validation_summary() {
    local results_dir="$1"
    local summary_file="$results_dir/VALIDATION_SUMMARY.md"
    
    log_info "Generating validation summary..."
    
    cat > "$summary_file" <<EOF
# Gemini Validation Summary: Strategic Tech Substack Strategy
**Analysis Date**: $(date +"%Y-%m-%d %H:%M:%S")
**Scope**: Market opportunity, competitive positioning, content strategy, business model

---

## Executive Summary

This validation analysis provides an independent assessment of the Strategic Tech Substack strategy targeting solo founders and small teams with agentic CLI tools.

### Key Findings Overview
- **Market Opportunity**: [To be reviewed from analysis]
- **Competitive Position**: [To be reviewed from analysis] 
- **Content Strategy**: [To be reviewed from analysis]
- **Business Model**: [To be reviewed from analysis]

---

## Market Opportunity Assessment

EOF

    if [[ -f "$results_dir/market_analysis.md" ]]; then
        echo "$(head -n 100 "$results_dir/market_analysis.md")" >> "$summary_file"
        echo -e "\n[📄 Full Market Analysis](./market_analysis.md)\n" >> "$summary_file"
    fi

    cat >> "$summary_file" <<EOF
---

## Competitive Intelligence

EOF

    if [[ -f "$results_dir/competitive_analysis.md" ]]; then
        echo "$(head -n 100 "$results_dir/competitive_analysis.md")" >> "$summary_file"
        echo -e "\n[📄 Full Competitive Analysis](./competitive_analysis.md)\n" >> "$summary_file"
    fi

    cat >> "$summary_file" <<EOF
---

## Content Strategy Assessment

EOF

    if [[ -f "$results_dir/content_gap_analysis.md" ]]; then
        echo "$(head -n 100 "$results_dir/content_gap_analysis.md")" >> "$summary_file"
        echo -e "\n[📄 Full Content Gap Analysis](./content_gap_analysis.md)\n" >> "$summary_file"
    fi

    cat >> "$summary_file" <<EOF
---

## Business Model Validation

EOF

    if [[ -f "$results_dir/business_model_validation.md" ]]; then
        echo "$(head -n 100 "$results_dir/business_model_validation.md")" >> "$summary_file"
        echo -e "\n[📄 Full Business Model Analysis](./business_model_validation.md)\n" >> "$summary_file"
    fi

    cat >> "$summary_file" <<EOF
---

## Strategic Recommendations

### Priority Actions
Based on the validation analysis, the following actions are recommended:

1. **Immediate (0-30 days)**
   - [ ] Address high-priority content gaps identified
   - [ ] Implement competitive differentiation strategies
   - [ ] Validate pricing model with target audience

2. **Short-term (1-3 months)**
   - [ ] Execute content production pipeline
   - [ ] Build community engagement infrastructure
   - [ ] Establish strategic partnerships

3. **Medium-term (3-6 months)**
   - [ ] Scale content distribution
   - [ ] Develop premium offerings
   - [ ] Optimize conversion funnel

### Risk Mitigation
Key risks and mitigation strategies:
- [To be extracted from analyses]

### Success Metrics to Track
- [To be defined based on analysis outcomes]

---

*This analysis was generated using Google Gemini AI for independent market validation.*
EOF

    log_success "Validation summary generated: $summary_file"
}

# Prepare context package
prepare_context_package() {
    local context_file="context_package.md"
    
    log_info "Preparing context package..."
    
    cat > "$context_file" <<EOF
# Strategic Tech Substack: Complete Context Package for Analysis

## Executive Summary
Target Market: Solo founders and 2-10 person teams seeking 10x productivity through agentic CLI tools
Value Proposition: Transform complex enterprise AI strategies into accessible, immediately actionable CLI workflows
Content Strategy: 52 weekly essays with practical implementations, ROI calculations, and business impact metrics

## Market Positioning Strategy
$(cat ../SUBSTACK_CLI_INSIGHTS_EXTRACTION.md 2>/dev/null || echo "CLI insights file not found")

## Content Strategy Framework
$(cat ../SUBSTACK_CONTENT_CALENDAR_2025.md 2>/dev/null || echo "Content calendar file not found")

## Implementation Examples  
$(cat ../SUBSTACK_FIRST_THREE_ESSAYS.md 2>/dev/null || echo "Essay outlines file not found")

## Technical Infrastructure Assets
- Synapse RAG System: 226 vectors with business intelligence
- LinkedIn Knowledge Base: 615+ extracted insights
- Knowledge Categories: Development practices, tool preferences, management philosophy
- Proven CLI Automation: Working productivity patterns and workflows

## Competitive Differentiation
- vs Generic Productivity: Real CLI implementations vs theoretical advice
- vs Enterprise AI: Resource-constrained solutions vs enterprise assumptions  
- vs Technical Tutorials: Business impact focus vs pure technical instruction

## Current Development Status
- Phase 1 Complete: Strategy development and market analysis
- Phase 2 Ready: Content production pipeline and community building
- Phase 3 Planned: Business development and revenue scaling

## Success Metrics Framework
- Content Engagement: Newsletter growth, essay engagement rates
- Community Building: Active user base, tool sharing, collaboration
- Business Conversion: Newsletter → consulting pipeline effectiveness
- Market Impact: Solo founder productivity improvements, competitive advantage creation
EOF

    log_success "Context package prepared: $context_file"
}

# Run complete validation
run_complete_validation() {
    local context_file="context_package.md"
    
    log_info "🚀 Starting comprehensive Gemini validation analysis"
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    
    # Prepare context
    prepare_context_package
    
    # Run validations in parallel for faster execution
    log_info "Running validation analyses..."
    
    validate_with_gemini "market_opportunity" "$context_file" "$RESULTS_DIR/market_analysis.md" &
    local pid1=$!
    
    validate_with_gemini "competitive_intelligence" "$context_file" "$RESULTS_DIR/competitive_analysis.md" &  
    local pid2=$!
    
    validate_with_gemini "content_gaps" "$context_file" "$RESULTS_DIR/content_gap_analysis.md" &
    local pid3=$!
    
    validate_with_gemini "business_model" "$context_file" "$RESULTS_DIR/business_model_validation.md" &
    local pid4=$!
    
    # Wait for all analyses to complete
    log_info "Waiting for analyses to complete..."
    wait $pid1 $pid2 $pid3 $pid4
    
    log_success "All Gemini validations complete!"
    
    # Generate summary report
    generate_validation_summary "$RESULTS_DIR"
    
    # Show results
    log_success "🎯 Validation analysis complete!"
    log_info "Results directory: $RESULTS_DIR"
    log_info "Summary report: $RESULTS_DIR/VALIDATION_SUMMARY.md"
    
    # Clean up
    rm -f context_package.md
}

# Main execution
main() {
    echo "🔬 Gemini Market Validation Tool"
    echo "================================="
    
    check_prerequisites
    run_complete_validation
    
    echo ""
    log_success "Analysis complete! Review the results to validate and optimize your strategy."
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi