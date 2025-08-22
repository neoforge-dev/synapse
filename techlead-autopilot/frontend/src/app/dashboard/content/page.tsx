"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { 
  Plus, 
  FileText, 
  CheckCircle, 
  Calendar, 
  TrendingUp, 
  Users,
  BarChart3,
  Target,
  Zap
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

import { contentApi, ContentGenerated } from "@/lib/api-client"
import { ContentList } from "@/components/content/content-list"

export default function ContentDashboardPage() {
  const [selectedContent, setSelectedContent] = useState<ContentGenerated | null>(null)

  // Fetch content analytics
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['content-analytics'],
    queryFn: () => contentApi.getAnalytics(30),
  })

  // Fetch recent content
  const { data: recentContent, isLoading: contentLoading } = useQuery({
    queryKey: ['content-recent'],
    queryFn: () => contentApi.list({ limit: 5 }),
  })

  const handleContentSelect = (content: ContentGenerated) => {
    setSelectedContent(content)
  }

  const statsCards = [
    {
      title: "Total Content",
      value: analytics?.total_content_generated || 0,
      description: "Generated this month",
      icon: FileText,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    {
      title: "Content Posted",
      value: analytics?.content_posted || 0,
      description: `${((analytics?.posting_rate || 0) * 100).toFixed(1)}% posting rate`,
      icon: CheckCircle,
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    {
      title: "Avg Engagement",
      value: `${((analytics?.average_engagement?.engagement_rate || 0) * 100).toFixed(1)}%`,
      description: "Across all posted content",
      icon: TrendingUp,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
    },
    {
      title: "Consultation Leads",
      value: analytics?.consultation_focus_performance?.consultation_leads || 0,
      description: "From consultation-focused posts",
      icon: Target,
      color: "text-orange-600",
      bgColor: "bg-orange-100",
    },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Content Management</h1>
              <p className="mt-2 text-gray-600">
                Create, manage, and track your LinkedIn content performance
              </p>
            </div>
            <Link href="/dashboard/content/generate">
              <Button className="bg-blue-600 hover:bg-blue-700">
                <Plus className="mr-2 h-4 w-4" />
                Generate Content
              </Button>
            </Link>
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
                  <div className="text-2xl font-bold text-gray-900">
                    {analyticsLoading ? (
                      <div className="h-8 bg-gray-200 rounded animate-pulse"></div>
                    ) : (
                      stat.value
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {stat.description}
                  </p>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Top Content Types Performance */}
        {analytics?.top_content_types && analytics.top_content_types.length > 0 && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Top Performing Content Types
              </CardTitle>
              <CardDescription>
                Content types with highest engagement rates this month
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {analytics.top_content_types.slice(0, 3).map((type, index) => (
                  <div key={type.content_type} className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">#{index + 1}</Badge>
                        <span className="font-medium">
                          {type.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </span>
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        {type.count} posts • {(type.avg_engagement * 100).toFixed(1)}% avg engagement
                      </div>
                    </div>
                    <TrendingUp className="h-5 w-5 text-green-600" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Content Tabs */}
        <Tabs defaultValue="all" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="all">All Content</TabsTrigger>
            <TabsTrigger value="draft">Drafts</TabsTrigger>
            <TabsTrigger value="approved">Approved</TabsTrigger>
            <TabsTrigger value="published">Published</TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="space-y-6">
            <ContentList onContentSelect={handleContentSelect} />
          </TabsContent>

          <TabsContent value="draft" className="space-y-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Draft Content</h3>
                <p className="text-sm text-gray-600">Content waiting for review and approval</p>
              </div>
            </div>
            <ContentList onContentSelect={handleContentSelect} />
          </TabsContent>

          <TabsContent value="approved" className="space-y-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Approved Content</h3>
                <p className="text-sm text-gray-600">Content approved and ready for scheduling</p>
              </div>
            </div>
            <ContentList onContentSelect={handleContentSelect} />
          </TabsContent>

          <TabsContent value="published" className="space-y-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Published Content</h3>
                <p className="text-sm text-gray-600">Content that has been posted to LinkedIn</p>
              </div>
              <Link href="/dashboard/analytics">
                <Button variant="outline" size="sm">
                  <BarChart3 className="mr-2 h-4 w-4" />
                  View Analytics
                </Button>
              </Link>
            </div>
            <ContentList onContentSelect={handleContentSelect} />
          </TabsContent>
        </Tabs>

        {/* Quick Actions for Recent Content */}
        {recentContent?.content && recentContent.content.length > 0 && (
          <Card className="mt-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Quick Actions
              </CardTitle>
              <CardDescription>
                Recent content that needs your attention
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentContent.content
                  .filter(content => content.status === 'draft')
                  .slice(0, 3)
                  .map((content) => (
                    <div key={content.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900 truncate">
                          {content.topic}
                        </div>
                        <div className="text-sm text-gray-500">
                          {content.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} • 
                          {(content.engagement_prediction * 100).toFixed(1)}% predicted engagement
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline">
                          Review
                        </Button>
                        <Button size="sm">
                          Approve
                        </Button>
                      </div>
                    </div>
                  ))}
                
                {recentContent.content.filter(content => content.status === 'draft').length === 0 && (
                  <div className="text-center py-4 text-gray-500">
                    No draft content requiring attention
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Content Preview Dialog */}
      <Dialog open={!!selectedContent} onOpenChange={() => setSelectedContent(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedContent?.topic}
              <Badge variant="outline">
                {selectedContent?.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </Badge>
            </DialogTitle>
            <DialogDescription>
              Engagement Prediction: {((selectedContent?.engagement_prediction || 0) * 100).toFixed(1)}% • 
              {selectedContent?.character_count} characters
            </DialogDescription>
          </DialogHeader>
          
          {selectedContent && (
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Hook</h4>
                <div className="bg-blue-50 border-l-4 border-blue-400 p-3 rounded-r-md">
                  <p className="text-gray-800">{selectedContent.hook}</p>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Body</h4>
                <div className="bg-gray-50 p-3 rounded-md">
                  <p className="text-gray-800 whitespace-pre-line">{selectedContent.body}</p>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Call to Action</h4>
                <div className="bg-green-50 border-l-4 border-green-400 p-3 rounded-r-md">
                  <p className="text-gray-800">{selectedContent.call_to_action}</p>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setSelectedContent(null)}>
                  Close
                </Button>
                <Button>
                  Edit Content
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}