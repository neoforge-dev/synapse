"use client"

import { useMemo } from "react"
import { 
  Target,
  Brain,
  TrendingUp,
  Building,
  User,
  MessageSquare,
  Clock,
  Zap,
  CheckCircle,
  AlertTriangle,
  Info
} from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

import { LeadDetected } from "@/lib/api-client"

interface LeadScoringVisualizationProps {
  lead: LeadDetected
  className?: string
}

interface ScoringFactor {
  name: string
  weight: number
  score: number
  description: string
  icon: React.ComponentType<any>
  color: string
  reasoning: string
}

export function LeadScoringVisualization({ lead, className }: LeadScoringVisualizationProps) {
  const scoringFactors = useMemo(() => {
    // Calculate individual scoring factors based on lead data
    const factors: ScoringFactor[] = [
      {
        name: "Content Quality",
        weight: 25,
        score: Math.min(10, Math.max(1, lead.content_text ? lead.content_text.length / 50 : 5)),
        description: "Quality and depth of the inquiry content",
        icon: MessageSquare,
        color: "text-blue-600",
        reasoning: lead.content_text 
          ? `${lead.content_text.length} characters suggest ${lead.content_text.length > 200 ? 'detailed' : 'brief'} inquiry`
          : "No content available for analysis"
      },
      {
        name: "Company Size",
        weight: 20,
        score: getCompanySizeScore(lead.company_size),
        description: "Estimated company size and budget capacity",
        icon: Building,
        color: "text-purple-600",
        reasoning: getCompanySizeReasoning(lead.company_size)
      },
      {
        name: "Contact Authority",
        weight: 20,
        score: getAuthorityScore(lead.author_title),
        description: "Decision-making authority of the contact",
        icon: User,
        color: "text-green-600",
        reasoning: getAuthorityReasoning(lead.author_title)
      },
      {
        name: "Technical Complexity",
        weight: 15,
        score: getTechnicalScore(lead.technical_complexity),
        description: "Technical complexity matching our expertise",
        icon: Brain,
        color: "text-orange-600",
        reasoning: getTechnicalReasoning(lead.technical_complexity)
      },
      {
        name: "Urgency Indicators",
        weight: 10,
        score: Math.min(10, (lead.urgency_indicators?.length || 0) * 3),
        description: "Urgency signals in the inquiry",
        icon: Zap,
        color: "text-red-600",
        reasoning: `${lead.urgency_indicators?.length || 0} urgency signals detected`
      },
      {
        name: "Response Timing",
        weight: 10,
        score: getTimingScore(lead.detected_at),
        description: "Optimal response window opportunity",
        icon: Clock,
        color: "text-yellow-600",
        reasoning: getTimingReasoning(lead.detected_at)
      }
    ]

    return factors
  }, [lead])

  const overallScore = useMemo(() => {
    return scoringFactors.reduce((sum, factor) => sum + (factor.score * factor.weight / 100), 0)
  }, [scoringFactors])

  const confidenceLevel = lead.confidence * 100
  const scoreColor = overallScore >= 8 ? "text-green-600" : overallScore >= 6 ? "text-yellow-600" : "text-red-600"
  const confidenceColor = confidenceLevel >= 80 ? "text-green-600" : confidenceLevel >= 60 ? "text-yellow-600" : "text-red-600"

  return (
    <TooltipProvider>
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            AI Lead Scoring Analysis
          </CardTitle>
          <CardDescription>
            Comprehensive AI-powered scoring with confidence factors and reasoning
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Overall Score Summary */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className={`text-4xl font-bold mb-2 ${scoreColor}`}>
                {overallScore.toFixed(1)}
              </div>
              <div className="text-sm font-medium text-gray-700 mb-1">Overall Score</div>
              <div className="text-xs text-gray-500">out of 10.0</div>
              <Badge 
                variant="outline" 
                className={`mt-2 ${scoreColor.replace('text-', 'border-').replace('600', '200')}`}
              >
                {overallScore >= 8 ? 'High Quality' : overallScore >= 6 ? 'Good Quality' : 'Requires Review'}
              </Badge>
            </div>
            
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className={`text-4xl font-bold mb-2 ${confidenceColor}`}>
                {confidenceLevel.toFixed(0)}%
              </div>
              <div className="text-sm font-medium text-gray-700 mb-1">AI Confidence</div>
              <div className="text-xs text-gray-500">accuracy estimate</div>
              <Badge 
                variant="outline" 
                className={`mt-2 ${confidenceColor.replace('text-', 'border-').replace('600', '200')}`}
              >
                {confidenceLevel >= 80 ? 'High Confidence' : confidenceLevel >= 60 ? 'Medium Confidence' : 'Low Confidence'}
              </Badge>
            </div>
          </div>

          <Separator />

          {/* Scoring Factors Breakdown */}
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-4">Scoring Factors Breakdown</h4>
            <div className="space-y-4">
              {scoringFactors.map((factor, index) => {
                const Icon = factor.icon
                const factorScore = factor.score * factor.weight / 100
                
                return (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full bg-gray-100 ${factor.color}`}>
                          <Icon className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{factor.name}</span>
                            <Badge variant="outline" className="text-xs">
                              {factor.weight}% weight
                            </Badge>
                            <Tooltip>
                              <TooltipTrigger>
                                <Info className="h-3 w-3 text-gray-400" />
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="max-w-xs">{factor.description}</p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                          <div className="text-sm text-gray-500 mt-1">
                            {factor.reasoning}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-gray-900">
                          {factor.score.toFixed(1)}/10
                        </div>
                        <div className="text-xs text-gray-500">
                          +{factorScore.toFixed(1)} points
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Factor Score</span>
                        <span className="text-xs font-medium">{factor.score.toFixed(1)}/10</span>
                      </div>
                      <Progress 
                        value={factor.score * 10} 
                        className="h-2" 
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <Separator />

          {/* Confidence Analysis */}
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-4">Confidence Analysis</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <CheckCircle className="h-6 w-6 text-blue-600 mx-auto mb-2" />
                <div className="text-sm font-medium text-blue-900">Data Quality</div>
                <div className="text-xs text-blue-700 mt-1">
                  {getDataQualityScore(lead)}% complete
                </div>
              </div>
              
              <div className="text-center p-3 bg-yellow-50 rounded-lg">
                <Brain className="h-6 w-6 text-yellow-600 mx-auto mb-2" />
                <div className="text-sm font-medium text-yellow-900">AI Analysis</div>
                <div className="text-xs text-yellow-700 mt-1">
                  {Math.round(lead.confidence * 100)}% confident
                </div>
              </div>
              
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <TrendingUp className="h-6 w-6 text-green-600 mx-auto mb-2" />
                <div className="text-sm font-medium text-green-900">Pattern Match</div>
                <div className="text-xs text-green-700 mt-1">
                  {getPatternMatchScore(lead)}% match
                </div>
              </div>
            </div>
          </div>

          {/* Recommendations */}
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-blue-600 mt-0.5" />
              <div>
                <div className="font-medium text-blue-900 mb-1">AI Recommendations</div>
                <div className="text-sm text-blue-800 space-y-1">
                  {getRecommendations(overallScore, confidenceLevel, lead).map((rec, index) => (
                    <div key={index}>• {rec}</div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </TooltipProvider>
  )
}

// Helper functions for scoring calculations
function getCompanySizeScore(companySize?: string): number {
  if (!companySize) return 5
  const size = companySize.toLowerCase()
  if (size.includes('enterprise') || size.includes('large')) return 9
  if (size.includes('medium') || size.includes('mid')) return 7
  if (size.includes('startup') || size.includes('small')) return 6
  return 5
}

function getCompanySizeReasoning(companySize?: string): string {
  if (!companySize) return "Company size not specified"
  const size = companySize.toLowerCase()
  if (size.includes('enterprise') || size.includes('large')) return "Large company with substantial budget"
  if (size.includes('medium') || size.includes('mid')) return "Medium company with good budget potential"
  if (size.includes('startup') || size.includes('small')) return "Small company with limited but focused budget"
  return "Company size unclear from available data"
}

function getAuthorityScore(title?: string): number {
  if (!title) return 4
  const t = title.toLowerCase()
  if (t.includes('ceo') || t.includes('founder') || t.includes('president')) return 10
  if (t.includes('cto') || t.includes('vp') || t.includes('director')) return 9
  if (t.includes('manager') || t.includes('lead')) return 7
  if (t.includes('engineer') || t.includes('developer')) return 5
  return 6
}

function getAuthorityReasoning(title?: string): string {
  if (!title) return "Job title not specified"
  const t = title.toLowerCase()
  if (t.includes('ceo') || t.includes('founder') || t.includes('president')) return "C-level executive with full decision authority"
  if (t.includes('cto') || t.includes('vp') || t.includes('director')) return "Senior leadership with significant influence"
  if (t.includes('manager') || t.includes('lead')) return "Management role with budget influence"
  if (t.includes('engineer') || t.includes('developer')) return "Technical role, may need management approval"
  return "Role authority unclear from title"
}

function getTechnicalScore(complexity?: string): number {
  if (!complexity) return 6
  const comp = complexity.toLowerCase()
  if (comp.includes('high') || comp.includes('complex')) return 9
  if (comp.includes('medium') || comp.includes('moderate')) return 7
  if (comp.includes('low') || comp.includes('simple')) return 5
  return 6
}

function getTechnicalReasoning(complexity?: string): string {
  if (!complexity) return "Technical complexity not assessed"
  const comp = complexity.toLowerCase()
  if (comp.includes('high') || comp.includes('complex')) return "High complexity matches our expertise perfectly"
  if (comp.includes('medium') || comp.includes('moderate')) return "Moderate complexity, good fit for our services"
  if (comp.includes('low') || comp.includes('simple')) return "Simple project, may not require our full expertise"
  return "Complexity level unclear from assessment"
}

function getTimingScore(detectedAt: string): number {
  const hoursAgo = (Date.now() - new Date(detectedAt).getTime()) / (1000 * 60 * 60)
  if (hoursAgo < 2) return 10
  if (hoursAgo < 12) return 8
  if (hoursAgo < 24) return 6
  if (hoursAgo < 72) return 4
  return 2
}

function getTimingReasoning(detectedAt: string): string {
  const hoursAgo = (Date.now() - new Date(detectedAt).getTime()) / (1000 * 60 * 60)
  if (hoursAgo < 2) return "Fresh inquiry - optimal response window"
  if (hoursAgo < 12) return "Recent inquiry - good response timing"
  if (hoursAgo < 24) return "Day-old inquiry - should respond soon"
  if (hoursAgo < 72) return "Several days old - response urgency increasing"
  return "Older inquiry - immediate response recommended"
}

function getDataQualityScore(lead: LeadDetected): number {
  let score = 0
  const fields = [
    lead.author_name,
    lead.author_title,
    lead.author_company,
    lead.content_text,
    lead.company_size,
    lead.technical_complexity
  ]
  fields.forEach(field => field && score++)
  return Math.round((score / fields.length) * 100)
}

function getPatternMatchScore(lead: LeadDetected): number {
  // Simple pattern matching based on known consultation indicators
  let score = 70 // Base score
  if (lead.inquiry_type === 'consultation') score += 20
  if (lead.urgency_indicators && lead.urgency_indicators.length > 0) score += 10
  return Math.min(100, score)
}

function getRecommendations(score: number, confidence: number, lead: LeadDetected): string[] {
  const recommendations = []
  
  if (score >= 8) {
    recommendations.push("High-value lead - prioritize immediate outreach")
  } else if (score >= 6) {
    recommendations.push("Solid opportunity - respond within 24 hours")
  } else {
    recommendations.push("Requires qualification - gather more information first")
  }
  
  if (confidence < 60) {
    recommendations.push("Low AI confidence - manual review recommended")
  }
  
  if (lead.urgency_indicators && lead.urgency_indicators.length > 0) {
    recommendations.push("Urgency detected - expedite response")
  }
  
  if (!lead.author_company || !lead.author_title) {
    recommendations.push("Research contact details before reaching out")
  }
  
  return recommendations
}