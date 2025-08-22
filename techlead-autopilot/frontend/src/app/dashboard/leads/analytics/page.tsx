"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { 
  ArrowLeft,
  TrendingUp, 
  Users, 
  Target, 
  DollarSign,
  Download,
  Calendar,
  BarChart3,
  PieChart,
  Activity
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

import { leadsApi, LeadAnalytics } from "@/lib/api-client"
import { LeadConversionTracker } from "@/components/leads/lead-conversion-tracker"

export default function LeadsAnalyticsPage() {
  const [timeRange, setTimeRange] = useState("30")

  // Fetch analytics data
  const { data: analytics, isLoading } = useQuery<LeadAnalytics>({
    queryKey: ['lead-analytics', timeRange],
    queryFn: () => leadsApi.getAnalytics(parseInt(timeRange)),
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 animate-pulse">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="h-8 bg-gray-200 rounded mb-6 w-1/3"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-96 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  const conversionRate = analytics?.total_leads ? 
    ((analytics.follow_up_status?.converted || 0) / analytics.total_leads * 100) : 0

  const avgDealSize = analytics?.conversion_metrics?.average_deal_size || 0
  const totalRevenue = analytics?.conversion_metrics?.total_revenue || 0

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center gap-4">
              <Link href="/dashboard/leads">
                <Button variant="ghost" className="p-2">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Lead Analytics</h1>
                <p className="mt-2 text-gray-600">
                  Comprehensive analysis of lead conversion and performance
                </p>
              </div>
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
                <Download className="mr-2 h-4 w-4" />
                Export Report
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Key Performance Indicators */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Leads</p>
                  <p className="text-3xl font-bold text-gray-900">{analytics?.total_leads || 0}</p>
                  <p className="text-sm text-gray-500">in last {timeRange} days</p>
                </div>
                <div className="p-3 rounded-full bg-blue-100">
                  <Users className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Conversion Rate</p>
                  <p className="text-3xl font-bold text-gray-900">{conversionRate.toFixed(1)}%</p>
                  <p className="text-sm text-gray-500">{analytics?.follow_up_status?.converted || 0} converted</p>
                </div>
                <div className="p-3 rounded-full bg-green-100">
                  <Target className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Avg Deal Size</p>
                  <p className="text-3xl font-bold text-gray-900">€{avgDealSize.toLocaleString()}</p>
                  <p className="text-sm text-gray-500">per consultation</p>
                </div>
                <div className="p-3 rounded-full bg-purple-100">
                  <DollarSign className="h-6 w-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Revenue</p>
                  <p className="text-3xl font-bold text-gray-900">€{(totalRevenue / 100).toLocaleString()}</p>
                  <p className="text-sm text-gray-500">pipeline value</p>
                </div>
                <div className="p-3 rounded-full bg-emerald-100">
                  <TrendingUp className="h-6 w-6 text-emerald-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Analytics Tabs */}
        <Tabs defaultValue="conversion" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="conversion">Conversion Pipeline</TabsTrigger>
            <TabsTrigger value="performance">Performance Trends</TabsTrigger>
            <TabsTrigger value="attribution">Content Attribution</TabsTrigger>
            <TabsTrigger value="quality">Lead Quality</TabsTrigger>
          </TabsList>

          {/* Conversion Pipeline Tab */}
          <TabsContent value="conversion">
            <LeadConversionTracker />
          </TabsContent>

          {/* Performance Trends Tab */}
          <TabsContent value="performance">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    Lead Volume Trends
                  </CardTitle>
                  <CardDescription>
                    Daily lead generation over the selected period
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="h-80 flex items-center justify-center bg-gray-50 rounded-lg">
                    <div className="text-center text-gray-500">
                      <BarChart3 className="h-12 w-12 mx-auto mb-4" />
                      <p>Lead volume chart would be rendered here</p>
                      <p className="text-sm">Integration with Recharts/Chart.js</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5" />
                    Conversion Rates
                  </CardTitle>
                  <CardDescription>
                    Conversion rate trends and improvements
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="h-80 flex items-center justify-center bg-gray-50 rounded-lg">
                    <div className="text-center text-gray-500">
                      <Activity className="h-12 w-12 mx-auto mb-4" />
                      <p>Conversion rate chart would be rendered here</p>
                      <p className="text-sm">Integration with Recharts/Chart.js</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Attribution Tab */}
          <TabsContent value="attribution">
            <Card>
              <CardHeader>
                <CardTitle>Content Attribution Analysis</CardTitle>
                <CardDescription>
                  Which content pieces generate the most valuable leads
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Top Performing Content */}
                  <div>
                    <h3 className="text-lg font-semibold mb-4">Top Performing Content</h3>
                    <div className="space-y-4">
                      {[
                        {
                          title: "Technical Leadership in Scaling Startups",
                          leads: 12,
                          value: 48000,
                          conversion: 25
                        },
                        {
                          title: "Engineering Team Structure Best Practices",
                          leads: 8,
                          value: 32000,
                          conversion: 37.5
                        },
                        {
                          title: "CTO Transition Challenges and Solutions",
                          leads: 6,
                          value: 30000,
                          conversion: 50
                        }
                      ].map((content, index) => (
                        <Card key={index} className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <h4 className="font-medium text-gray-900 mb-2">{content.title}</h4>
                              <div className="flex items-center gap-6 text-sm text-gray-600">
                                <span>{content.leads} leads generated</span>
                                <span>€{content.value.toLocaleString()} total value</span>
                                <span>{content.conversion}% conversion rate</span>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-lg font-bold text-gray-900">
                                #{index + 1}
                              </div>
                            </div>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>

                  <Separator />

                  {/* Platform Performance */}
                  <div>
                    <h3 className="text-lg font-semibold mb-4">Platform Performance</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <Card className="p-4 text-center">
                        <div className="text-2xl font-bold text-blue-600 mb-1">85%</div>
                        <div className="text-sm font-medium text-gray-900">LinkedIn</div>
                        <div className="text-xs text-gray-500">Most effective platform</div>
                      </Card>
                      
                      <Card className="p-4 text-center">
                        <div className="text-2xl font-bold text-purple-600 mb-1">12%</div>
                        <div className="text-sm font-medium text-gray-900">Twitter/X</div>
                        <div className="text-xs text-gray-500">Growing engagement</div>
                      </Card>
                      
                      <Card className="p-4 text-center">
                        <div className="text-2xl font-bold text-green-600 mb-1">3%</div>
                        <div className="text-sm font-medium text-gray-900">Direct</div>
                        <div className="text-xs text-gray-500">High-quality referrals</div>
                      </Card>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Lead Quality Tab */}
          <TabsContent value="quality">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="h-5 w-5" />
                    Lead Quality Distribution
                  </CardTitle>
                  <CardDescription>
                    Distribution of leads by quality score
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[
                      { range: "9-10", label: "Excellent", count: analytics?.leads_by_priority?.urgent || 0, color: "bg-green-500" },
                      { range: "7-8", label: "Good", count: analytics?.leads_by_priority?.high || 0, color: "bg-blue-500" },
                      { range: "5-6", label: "Average", count: analytics?.leads_by_priority?.medium || 0, color: "bg-yellow-500" },
                      { range: "1-4", label: "Poor", count: analytics?.leads_by_priority?.low || 0, color: "bg-gray-500" }
                    ].map((quality, index) => {
                      const percentage = analytics?.total_leads ? 
                        (quality.count / analytics.total_leads * 100) : 0
                      
                      return (
                        <div key={index} className="flex items-center gap-4">
                          <div className="w-16 text-sm font-medium text-gray-700">
                            {quality.range}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm text-gray-900">{quality.label}</span>
                              <span className="text-sm font-medium">{quality.count} leads</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div 
                                className={`h-2 rounded-full ${quality.color}`}
                                style={{ width: `${percentage}%` }}
                              ></div>
                            </div>
                          </div>
                          <div className="w-12 text-right text-sm text-gray-600">
                            {percentage.toFixed(0)}%
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Response Time Analysis</CardTitle>
                  <CardDescription>
                    Average response times by lead quality
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600 mb-1">
                        {analytics?.lead_quality_metrics?.average_response_time || 0}h
                      </div>
                      <div className="text-sm font-medium text-blue-900">Average Response Time</div>
                      <div className="text-xs text-blue-700 mt-1">
                        Across all lead qualities
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-center text-sm">
                      <div className="p-3 border rounded-lg">
                        <div className="font-semibold text-gray-900">High Quality</div>
                        <div className="text-green-600">2.1h avg</div>
                      </div>
                      <div className="p-3 border rounded-lg">
                        <div className="font-semibold text-gray-900">Low Quality</div>
                        <div className="text-gray-600">18.5h avg</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}