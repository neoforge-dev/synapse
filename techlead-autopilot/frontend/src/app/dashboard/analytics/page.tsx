"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { 
  TrendingUp, 
  Users, 
  FileText, 
  Target, 
  Calendar,
  DollarSign,
  BarChart3,
  PieChart,
  LineChart,
  Filter
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"

import { contentApi, leadsApi } from "@/lib/api-client"
import { EngagementTrendsChart } from "@/components/analytics/engagement-trends-chart"
import { ContentTypePerformanceChart } from "@/components/analytics/content-type-performance-chart"
import { ContentToLeadAttributionChart } from "@/components/analytics/content-to-lead-attribution-chart"
import { AnalyticsCards } from "@/components/analytics/analytics-cards"

export default function AnalyticsDashboardPage() {
  const [timeRange, setTimeRange] = useState("30")

  // Fetch content analytics
  const { data: contentAnalytics, isLoading: contentLoading } = useQuery({
    queryKey: ['content-analytics', timeRange],
    queryFn: () => contentApi.getAnalytics(parseInt(timeRange)),
  })

  // Fetch leads analytics
  const { data: leadsAnalytics, isLoading: leadsLoading } = useQuery({
    queryKey: ['leads-analytics', timeRange],
    queryFn: () => leadsApi.getAnalytics(parseInt(timeRange)),
  })

  // Fetch content-to-lead attribution
  const { data: attributionData, isLoading: attributionLoading } = useQuery({
    queryKey: ['attribution-analytics', timeRange],
    queryFn: () => leadsApi.getAttribution(parseInt(timeRange)),
  })

  const isLoading = contentLoading || leadsLoading || attributionLoading

  // Calculate derived metrics
  const totalValue = leadsAnalytics?.conversion_metrics?.total_revenue || 0
  const avgDealSize = leadsAnalytics?.conversion_metrics?.average_deal_size || 0
  const conversionRate = leadsAnalytics?.conversion_metrics?.conversion_rate || 0
  const leadVelocity = leadsAnalytics?.lead_quality_metrics?.average_response_time || 0

  const performanceMetrics = [
    {
      title: "Content Generated",
      value: contentAnalytics?.total_content_generated || 0,
      change: "+12%",
      changeType: "positive" as const,
      icon: FileText,
      description: `${contentAnalytics?.content_posted || 0} posted (${((contentAnalytics?.posting_rate || 0) * 100).toFixed(1)}% rate)`,
    },
    {
      title: "Avg Engagement Rate",
      value: `${((contentAnalytics?.average_engagement?.engagement_rate || 0) * 100).toFixed(1)}%`,
      change: "+2.3%",
      changeType: "positive" as const,
      icon: TrendingUp,
      description: `${contentAnalytics?.average_engagement?.likes || 0} avg likes per post`,
    },
    {
      title: "Leads Generated",
      value: leadsAnalytics?.total_leads || 0,
      change: "+8%",
      changeType: "positive" as const,
      icon: Users,
      description: `${leadsAnalytics?.leads_by_priority?.high || 0} high-priority leads`,
    },
    {
      title: "Pipeline Value",
      value: `€${(totalValue / 100).toLocaleString()}`,
      change: "+15%",
      changeType: "positive" as const,
      icon: DollarSign,
      description: `€${avgDealSize / 100} avg deal size`,
    },
    {
      title: "Conversion Rate",
      value: `${(conversionRate * 100).toFixed(1)}%`,
      change: "+1.2%",
      changeType: "positive" as const,
      icon: Target,
      description: `${leadVelocity}h avg response time`,
    },
    {
      title: "Content ROI",
      value: `${(totalValue > 0 ? (totalValue / ((contentAnalytics?.total_content_generated || 1) * 100)) : 0).toFixed(0)}x`,
      change: "+5.4%",
      changeType: "positive" as const,
      icon: BarChart3,
      description: "Revenue per content piece",
    },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
              <p className="mt-2 text-gray-600">
                Track content performance, lead generation, and ROI attribution
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-[180px]">
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
              <Button variant="outline">
                <Filter className="mr-2 h-4 w-4" />
                Export Data
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6 mb-8">
          {performanceMetrics.map((metric) => {
            const Icon = metric.icon
            return (
              <Card key={metric.title}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-600">{metric.title}</p>
                      <div className="flex items-baseline gap-2">
                        <p className="text-2xl font-bold text-gray-900">
                          {isLoading ? "..." : metric.value}
                        </p>
                        <Badge 
                          variant="outline" 
                          className={
                            metric.changeType === 'positive' 
                              ? 'text-green-600 border-green-200' 
                              : 'text-red-600 border-red-200'
                          }
                        >
                          {metric.change}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{metric.description}</p>
                    </div>
                    <Icon className="h-8 w-8 text-gray-400" />
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Analytics Tabs */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="content">Content Performance</TabsTrigger>
            <TabsTrigger value="leads">Lead Analytics</TabsTrigger>
            <TabsTrigger value="attribution">Attribution</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Engagement Trends */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <LineChart className="h-5 w-5" />
                    Engagement Trends
                  </CardTitle>
                  <CardDescription>
                    Daily engagement rate over the selected period
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <EngagementTrendsChart data={contentAnalytics} isLoading={isLoading} />
                </CardContent>
              </Card>

              {/* Top Content Types */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="h-5 w-5" />
                    Content Type Performance
                  </CardTitle>
                  <CardDescription>
                    Engagement rate by content type
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ContentTypePerformanceChart data={contentAnalytics?.top_content_types} isLoading={isLoading} />
                </CardContent>
              </Card>
            </div>

            {/* Consultation Focus Performance */}
            <Card>
              <CardHeader>
                <CardTitle>Consultation-Focused Content Performance</CardTitle>
                <CardDescription>
                  Compare performance between consultation-focused and regular content
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-blue-600">
                      {contentAnalytics?.consultation_focus_performance?.consultation_focused_posts || 0}
                    </div>
                    <div className="text-sm text-gray-600">Consultation Posts</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-gray-600">
                      {contentAnalytics?.consultation_focus_performance?.regular_posts || 0}
                    </div>
                    <div className="text-sm text-gray-600">Regular Posts</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-green-600">
                      {contentAnalytics?.consultation_focus_performance?.consultation_leads || 0}
                    </div>
                    <div className="text-sm text-gray-600">Consultation Leads</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-orange-600">
                      {contentAnalytics?.consultation_focus_performance?.regular_leads || 0}
                    </div>
                    <div className="text-sm text-gray-600">Regular Leads</div>
                  </div>
                </div>
                
                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-2">Key Insights</h4>
                  <ul className="text-sm text-blue-800 space-y-1">
                    <li>• Consultation-focused content generates {
                      contentAnalytics?.consultation_focus_performance ? 
                      ((contentAnalytics.consultation_focus_performance.consultation_leads / Math.max(contentAnalytics.consultation_focus_performance.consultation_focused_posts, 1)) * 100).toFixed(1) : 0
                    }% more leads per post</li>
                    <li>• Higher engagement rate on consultation-focused content</li>
                    <li>• Better qualification rate for consultation opportunities</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Content Performance Tab */}
          <TabsContent value="content" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Content Volume */}
              <Card>
                <CardHeader>
                  <CardTitle>Content Volume</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Generated</span>
                      <span className="font-semibold">{contentAnalytics?.total_content_generated || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Posted</span>
                      <span className="font-semibold">{contentAnalytics?.content_posted || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Posting Rate</span>
                      <span className="font-semibold">{((contentAnalytics?.posting_rate || 0) * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Engagement Metrics */}
              <Card>
                <CardHeader>
                  <CardTitle>Engagement Metrics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Avg Engagement</span>
                      <span className="font-semibold">{((contentAnalytics?.average_engagement?.engagement_rate || 0) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Avg Likes</span>
                      <span className="font-semibold">{contentAnalytics?.average_engagement?.likes || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Avg Comments</span>
                      <span className="font-semibold">{contentAnalytics?.average_engagement?.comments || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Avg Shares</span>
                      <span className="font-semibold">{contentAnalytics?.average_engagement?.shares || 0}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Top Performing Types */}
              <Card>
                <CardHeader>
                  <CardTitle>Top Content Types</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {contentAnalytics?.top_content_types?.slice(0, 5).map((type, index) => (
                      <div key={type.content_type} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">#{index + 1}</Badge>
                          <span className="text-sm font-medium">
                            {type.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold">{(type.avg_engagement * 100).toFixed(1)}%</div>
                          <div className="text-xs text-gray-500">{type.count} posts</div>
                        </div>
                      </div>
                    )) || []}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Lead Analytics Tab */}
          <TabsContent value="leads" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Lead Quality Distribution */}
              <Card>
                <CardHeader>
                  <CardTitle>Lead Priority Distribution</CardTitle>
                  <CardDescription>
                    Breakdown of leads by priority level
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(leadsAnalytics?.leads_by_priority || {}).map(([priority, count]) => (
                      <div key={priority} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge 
                            className={
                              priority === 'urgent' ? 'bg-red-100 text-red-800' :
                              priority === 'high' ? 'bg-orange-100 text-orange-800' :
                              priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }
                          >
                            {priority.charAt(0).toUpperCase() + priority.slice(1)}
                          </Badge>
                        </div>
                        <span className="font-semibold">{count}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Conversion Metrics */}
              <Card>
                <CardHeader>
                  <CardTitle>Conversion Metrics</CardTitle>
                  <CardDescription>
                    Lead to consultation conversion data
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Conversion Rate</span>
                      <span className="font-semibold">{(conversionRate * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Total Revenue</span>
                      <span className="font-semibold">€{(totalValue / 100).toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Avg Deal Size</span>
                      <span className="font-semibold">€{avgDealSize / 100}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Avg Response Time</span>
                      <span className="font-semibold">{leadVelocity}h</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Attribution Tab */}
          <TabsContent value="attribution" className="space-y-6">
            <ContentToLeadAttributionChart 
              data={attributionData} 
              isLoading={attributionLoading}
              timeRange={parseInt(timeRange)}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}