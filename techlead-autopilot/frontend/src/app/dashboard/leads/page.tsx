"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { 
  Users, 
  Target, 
  DollarSign, 
  Clock, 
  AlertTriangle,
  TrendingUp,
  Plus,
  Filter,
  Download,
  Bell,
  MessageSquare,
  Calendar
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

import { leadsApi } from "@/lib/api-client"
import { LeadList } from "@/components/leads/lead-list"

export default function LeadsDashboardPage() {
  const [timeRange, setTimeRange] = useState("30")

  // Fetch lead analytics
  const { data: leadAnalytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['lead-analytics', timeRange],
    queryFn: () => leadsApi.getAnalytics(parseInt(timeRange)),
  })

  // Fetch high priority leads
  const { data: highPriorityLeads, isLoading: highPriorityLoading } = useQuery({
    queryKey: ['high-priority-leads'],
    queryFn: () => leadsApi.getHighPriority(24),
  })

  const statsCards = [
    {
      title: "Total Leads",
      value: leadAnalytics?.total_leads || 0,
      description: `In last ${timeRange} days`,
      icon: Users,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
      change: "+12%",
      changeType: "positive" as const,
    },
    {
      title: "Conversion Rate",
      value: `${((leadAnalytics?.conversion_metrics?.conversion_rate || 0) * 100).toFixed(1)}%`,
      description: "Lead to consultation",
      icon: Target,
      color: "text-green-600",
      bgColor: "bg-green-100",
      change: "+2.3%",
      changeType: "positive" as const,
    },
    {
      title: "Pipeline Value",
      value: `€${((leadAnalytics?.conversion_metrics?.total_revenue || 0) / 100).toLocaleString()}`,
      description: "Total estimated value",
      icon: DollarSign,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
      change: "+8.7%",
      changeType: "positive" as const,
    },
    {
      title: "Avg Response Time",
      value: `${leadAnalytics?.lead_quality_metrics?.average_response_time || 0}h`,
      description: "First response time",
      icon: Clock,
      color: "text-orange-600",
      bgColor: "bg-orange-100",
      change: "-1.2h",
      changeType: "positive" as const,
    },
  ]

  const priorityDistribution = [
    {
      priority: "urgent",
      count: leadAnalytics?.leads_by_priority?.urgent || 0,
      color: "bg-red-500",
      textColor: "text-red-700",
      bgColor: "bg-red-50",
      label: "Urgent",
      description: "Requires immediate attention",
    },
    {
      priority: "high",
      count: leadAnalytics?.leads_by_priority?.high || 0,
      color: "bg-orange-500",
      textColor: "text-orange-700",
      bgColor: "bg-orange-50",
      label: "High",
      description: "High-value opportunities",
    },
    {
      priority: "medium",
      count: leadAnalytics?.leads_by_priority?.medium || 0,
      color: "bg-yellow-500",
      textColor: "text-yellow-700",
      bgColor: "bg-yellow-50",
      label: "Medium",
      description: "Standard follow-up needed",
    },
    {
      priority: "low",
      count: leadAnalytics?.leads_by_priority?.low || 0,
      color: "bg-gray-500",
      textColor: "text-gray-700",
      bgColor: "bg-gray-50",
      label: "Low",
      description: "Long-term nurturing",
    },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Lead Management</h1>
              <p className="mt-2 text-gray-600">
                Track and manage consultation opportunities from LinkedIn content
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
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
              <Button variant="outline">
                <Filter className="mr-2 h-4 w-4" />
                Filter
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statsCards.map((stat) => {
            const Icon = stat.icon
            return (
              <Card key={stat.title}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-gray-600">
                    {stat.title}
                  </CardTitle>
                  <div className={`p-2 rounded-full ${stat.bgColor}`}>
                    <Icon className={`h-4 w-4 ${stat.color}`} />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-2">
                    <div className="text-2xl font-bold text-gray-900">
                      {analyticsLoading ? (
                        <div className="h-8 bg-gray-200 rounded animate-pulse w-16"></div>
                      ) : (
                        stat.value
                      )}
                    </div>
                    <Badge 
                      variant="outline" 
                      className={
                        stat.changeType === 'positive' 
                          ? 'text-green-600 border-green-200' 
                          : 'text-red-600 border-red-200'
                      }
                    >
                      {stat.change}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {stat.description}
                  </p>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Priority Distribution */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Lead Priority Distribution
            </CardTitle>
            <CardDescription>
              Breakdown of leads by priority level requiring different response times
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {priorityDistribution.map((priority) => (
                <div key={priority.priority} className={`p-4 rounded-lg ${priority.bgColor} border border-opacity-20`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className={`w-3 h-3 rounded-full ${priority.color}`}></div>
                    <span className="text-2xl font-bold text-gray-900">
                      {analyticsLoading ? (
                        <div className="h-6 bg-gray-200 rounded animate-pulse w-8"></div>
                      ) : (
                        priority.count
                      )}
                    </span>
                  </div>
                  <div className={`font-semibold ${priority.textColor} mb-1`}>
                    {priority.label} Priority
                  </div>
                  <div className="text-xs text-gray-600">
                    {priority.description}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* High Priority Alerts */}
        {highPriorityLeads && highPriorityLeads.leads && highPriorityLeads.leads.length > 0 && (
          <Card className="mb-8 border-red-200 bg-red-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-800">
                <Bell className="h-5 w-5" />
                High Priority Leads ({highPriorityLeads.count})
              </CardTitle>
              <CardDescription className="text-red-600">
                These leads require immediate attention within the next 24 hours
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {highPriorityLeads.leads.slice(0, 3).map((lead: any) => (
                  <div key={lead.id} className="flex items-center justify-between p-3 bg-white rounded-lg border">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-gray-900">{lead.author_name}</span>
                        <Badge variant="outline" className="text-xs">
                          {lead.inquiry_type.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                        </Badge>
                        <Badge 
                          className={
                            lead.priority === 'urgent' ? 'bg-red-100 text-red-800' : 'bg-orange-100 text-orange-800'
                          }
                        >
                          {lead.priority.charAt(0).toUpperCase() + lead.priority.slice(1)}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-600">
                        {lead.company_size} • Score: {lead.lead_score}/10 • 
                        €{lead.estimated_value_euros.toLocaleString()} potential value
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {lead.follow_up_suggested}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline">
                        <MessageSquare className="mr-1 h-3 w-3" />
                        Contact
                      </Button>
                      <Link href={`/dashboard/leads/${lead.id}`}>
                        <Button size="sm">
                          View Details
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
                
                {highPriorityLeads.leads.length > 3 && (
                  <div className="text-center pt-2">
                    <Button variant="outline" size="sm">
                      View All {highPriorityLeads.count} High Priority Leads
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Lead Management Tabs */}
        <Tabs defaultValue="all" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="all">All Leads</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="contacted">Contacted</TabsTrigger>
            <TabsTrigger value="qualified">Qualified</TabsTrigger>
            <TabsTrigger value="converted">Converted</TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">All Leads</h3>
                <p className="text-sm text-gray-600">Complete list of detected consultation opportunities</p>
              </div>
              <Link href="/dashboard/analytics">
                <Button variant="outline" size="sm">
                  <TrendingUp className="mr-2 h-4 w-4" />
                  View Analytics
                </Button>
              </Link>
            </div>
            <LeadList />
          </TabsContent>

          <TabsContent value="pending" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Pending Follow-up</h3>
                <p className="text-sm text-gray-600">Leads awaiting initial contact</p>
              </div>
            </div>
            <LeadList filterStatus="pending" />
          </TabsContent>

          <TabsContent value="contacted" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Contacted</h3>
                <p className="text-sm text-gray-600">Leads that have been contacted and are in progress</p>
              </div>
            </div>
            <LeadList filterStatus="contacted" />
          </TabsContent>

          <TabsContent value="qualified" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Qualified</h3>
                <p className="text-sm text-gray-600">Qualified leads ready for consultation scheduling</p>
              </div>
            </div>
            <LeadList filterStatus="qualified" />
          </TabsContent>

          <TabsContent value="converted" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Converted</h3>
                <p className="text-sm text-gray-600">Successfully converted leads with consultation bookings</p>
              </div>
            </div>
            <LeadList filterStatus="converted" />
          </TabsContent>
        </Tabs>

        {/* Quick Actions */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Quick Actions
            </CardTitle>
            <CardDescription>
              Common lead management tasks and shortcuts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button variant="outline" className="h-auto p-4 flex flex-col items-start">
                <MessageSquare className="h-5 w-5 mb-2" />
                <span className="font-medium">Bulk Contact</span>
                <span className="text-xs text-gray-500">Send follow-up to multiple leads</span>
              </Button>
              
              <Button variant="outline" className="h-auto p-4 flex flex-col items-start">
                <Download className="h-5 w-5 mb-2" />
                <span className="font-medium">Export Leads</span>
                <span className="text-xs text-gray-500">Download lead data for external CRM</span>
              </Button>
              
              <Button variant="outline" className="h-auto p-4 flex flex-col items-start">
                <TrendingUp className="h-5 w-5 mb-2" />
                <span className="font-medium">Performance Review</span>
                <span className="text-xs text-gray-500">Analyze lead conversion patterns</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}