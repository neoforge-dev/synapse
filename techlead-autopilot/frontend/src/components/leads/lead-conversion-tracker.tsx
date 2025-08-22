"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { 
  TrendingUp, 
  Users, 
  Target, 
  DollarSign, 
  Clock,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Activity,
  Calendar,
  Filter,
  Download
} from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"

import { leadsApi, LeadAnalytics, LeadDetected } from "@/lib/api-client"

interface ConversionStage {
  name: string
  key: string
  color: string
  bgColor: string
  icon: React.ComponentType<any>
  description: string
}

const conversionStages: ConversionStage[] = [
  {
    name: "New Leads",
    key: "new",
    color: "text-blue-600",
    bgColor: "bg-blue-100",
    icon: Users,
    description: "Fresh inquiries detected"
  },
  {
    name: "Pending",
    key: "pending", 
    color: "text-yellow-600",
    bgColor: "bg-yellow-100",
    icon: Clock,
    description: "Awaiting initial contact"
  },
  {
    name: "Contacted",
    key: "contacted",
    color: "text-purple-600", 
    bgColor: "bg-purple-100",
    icon: Activity,
    description: "Initial contact made"
  },
  {
    name: "Qualified",
    key: "qualified",
    color: "text-green-600",
    bgColor: "bg-green-100", 
    icon: Target,
    description: "Qualified opportunities"
  },
  {
    name: "Converted",
    key: "converted",
    color: "text-emerald-600",
    bgColor: "bg-emerald-100",
    icon: CheckCircle,
    description: "Won consultations"
  },
  {
    name: "Lost",
    key: "lost",
    color: "text-gray-600",
    bgColor: "bg-gray-100",
    icon: AlertCircle,
    description: "Lost opportunities"
  }
]

interface LeadConversionTrackerProps {
  className?: string
}

export function LeadConversionTracker({ className }: LeadConversionTrackerProps) {
  const [timeRange, setTimeRange] = useState("30")
  const [viewMode, setViewMode] = useState<"funnel" | "timeline">("funnel")

  // Fetch analytics data
  const { data: analytics, isLoading: analyticsLoading } = useQuery<LeadAnalytics>({
    queryKey: ['lead-analytics', timeRange],
    queryFn: () => leadsApi.getAnalytics(parseInt(timeRange)),
  })

  // Fetch attribution data
  const { data: attributionData, isLoading: attributionLoading } = useQuery({
    queryKey: ['lead-attribution', timeRange],
    queryFn: () => leadsApi.getAttribution(parseInt(timeRange)),
  })

  if (analyticsLoading || attributionLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <div className="h-6 bg-gray-200 rounded animate-pulse w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded animate-pulse"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const stageData = conversionStages.map(stage => ({
    ...stage,
    count: analytics?.follow_up_status?.[stage.key as keyof typeof analytics.follow_up_status] || 0
  }))

  // Calculate conversion rates
  const totalLeads = analytics?.total_leads || 0
  const convertedLeads = analytics?.follow_up_status?.converted || 0
  const qualifiedLeads = analytics?.follow_up_status?.qualified || 0
  const contactedLeads = analytics?.follow_up_status?.contacted || 0

  const conversionRate = totalLeads > 0 ? (convertedLeads / totalLeads) * 100 : 0
  const qualificationRate = totalLeads > 0 ? ((qualifiedLeads + convertedLeads) / totalLeads) * 100 : 0
  const contactRate = totalLeads > 0 ? ((contactedLeads + qualifiedLeads + convertedLeads) / totalLeads) * 100 : 0

  const avgDealSize = analytics?.conversion_metrics?.average_deal_size || 0
  const totalRevenue = analytics?.conversion_metrics?.total_revenue || 0

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Lead Conversion Pipeline
              </CardTitle>
              <CardDescription>
                Track lead progression from inquiry to consultation
              </CardDescription>
            </div>
            <div className="flex items-center gap-4">
              <Select value={viewMode} onValueChange={(value: "funnel" | "timeline") => setViewMode(value)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="funnel">Funnel View</SelectItem>
                  <SelectItem value="timeline">Timeline View</SelectItem>
                </SelectContent>
              </Select>
              
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-[140px]">
                  <Calendar className="mr-2 h-4 w-4" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">Last 7 days</SelectItem>
                  <SelectItem value="30">Last 30 days</SelectItem>
                  <SelectItem value="90">Last 90 days</SelectItem>
                  <SelectItem value="365">Last year</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-gray-700">Total Leads</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{totalLeads}</div>
            <div className="text-sm text-gray-500">in last {timeRange} days</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium text-gray-700">Conversion Rate</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{conversionRate.toFixed(1)}%</div>
            <div className="text-sm text-gray-500">{convertedLeads} converted</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-purple-600" />
              <span className="text-sm font-medium text-gray-700">Avg Deal Size</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">€{avgDealSize.toLocaleString()}</div>
            <div className="text-sm text-gray-500">per consultation</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-emerald-600" />
              <span className="text-sm font-medium text-gray-700">Total Revenue</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">€{(totalRevenue / 100).toLocaleString()}</div>
            <div className="text-sm text-gray-500">pipeline value</div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Visualization */}
      {viewMode === "funnel" ? (
        <Card>
          <CardHeader>
            <CardTitle>Conversion Funnel</CardTitle>
            <CardDescription>
              Lead progression through conversion stages
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {stageData.slice(0, -1).map((stage, index) => {
              const nextStage = stageData[index + 1]
              const conversionToNext = stage.count > 0 ? (nextStage?.count || 0) / stage.count * 100 : 0
              const Icon = stage.icon
              
              return (
                <div key={stage.key}>
                  <div className="flex items-center justify-between p-4 rounded-lg border">
                    <div className="flex items-center gap-4 flex-1">
                      <div className={`p-3 rounded-full ${stage.bgColor}`}>
                        <Icon className={`h-5 w-5 ${stage.color}`} />
                      </div>
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-gray-900">{stage.name}</h3>
                          <Badge variant="outline">{stage.count} leads</Badge>
                          {totalLeads > 0 && (
                            <Badge variant="secondary">
                              {((stage.count / totalLeads) * 100).toFixed(1)}% of total
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-600">{stage.description}</p>
                        
                        {/* Progress bar showing relative volume */}
                        <div className="mt-3">
                          <Progress 
                            value={totalLeads > 0 ? (stage.count / totalLeads) * 100 : 0} 
                            className="h-2"
                          />
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <div className="text-2xl font-bold text-gray-900">{stage.count}</div>
                        {nextStage && (
                          <div className="text-sm text-gray-500">
                            {conversionToNext.toFixed(1)}% convert
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Arrow between stages */}
                  {index < stageData.length - 2 && (
                    <div className="flex justify-center py-2">
                      <ArrowRight className="h-5 w-5 text-gray-400" />
                    </div>
                  )}
                </div>
              )
            })}
            
            <Separator />
            
            {/* Lost leads separately */}
            <div className="p-4 rounded-lg border border-gray-200 bg-gray-50">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-full bg-gray-100">
                  <AlertCircle className="h-5 w-5 text-gray-600" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold text-gray-900">Lost Opportunities</h3>
                    <Badge variant="outline">{stageData[5].count} leads</Badge>
                  </div>
                  <p className="text-sm text-gray-600">Opportunities that didn't convert</p>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-gray-700">{stageData[5].count}</div>
                  <div className="text-sm text-gray-500">
                    {totalLeads > 0 ? ((stageData[5].count / totalLeads) * 100).toFixed(1) : 0}% of total
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Timeline View</CardTitle>
            <CardDescription>
              Conversion rates and trends over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600 mb-1">
                  {contactRate.toFixed(1)}%
                </div>
                <div className="text-sm font-medium text-blue-900">Contact Rate</div>
                <div className="text-xs text-blue-700 mt-1">
                  Leads receiving initial contact
                </div>
              </div>
              
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600 mb-1">
                  {qualificationRate.toFixed(1)}%
                </div>
                <div className="text-sm font-medium text-green-900">Qualification Rate</div>
                <div className="text-xs text-green-700 mt-1">
                  Leads progressing to qualification
                </div>
              </div>
              
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600 mb-1">
                  {conversionRate.toFixed(1)}%
                </div>
                <div className="text-sm font-medium text-purple-900">Final Conversion</div>
                <div className="text-xs text-purple-700 mt-1">
                  Leads becoming consultations
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Attribution Analysis */}
      {attributionData?.content_performance && (
        <Card>
          <CardHeader>
            <CardTitle>Content Attribution</CardTitle>
            <CardDescription>
              Which content generates the most valuable leads
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {attributionData.content_performance.slice(0, 5).map((content: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-4 rounded-lg border">
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 mb-1">
                      {content.content_title || `Content #${index + 1}`}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span>{content.leads_generated} leads</span>
                      <span>€{content.total_value} value</span>
                      <span>{content.conversion_rate}% conversion</span>
                    </div>
                  </div>
                  <Badge 
                    variant={index < 2 ? "default" : "secondary"}
                    className="ml-4"
                  >
                    #{index + 1}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}