"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { 
  ArrowLeft, 
  Edit3, 
  CheckCircle, 
  Calendar, 
  Share2, 
  Trash2,
  Save,
  X,
  TrendingUp,
  Users,
  Clock,
  Target,
  BarChart3
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

import { contentApi } from "@/lib/api-client"

interface ContentDetailPageProps {
  params: {
    id: string
  }
}

export default function ContentDetailPage({ params }: ContentDetailPageProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editedContent, setEditedContent] = useState({
    hook: "",
    body: "",
    call_to_action: "",
    hashtags: "",
  })
  
  const router = useRouter()
  const queryClient = useQueryClient()

  const { data: content, isLoading, error } = useQuery({
    queryKey: ['content', params.id],
    queryFn: () => contentApi.get(params.id),
  })

  const approveContentMutation = useMutation({
    mutationFn: () => contentApi.approve(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
    },
  })

  const deleteContentMutation = useMutation({
    mutationFn: () => contentApi.delete(params.id),
    onSuccess: () => {
      router.push('/dashboard/content')
    },
  })

  // Initialize edited content when content loads
  if (content && !isEditing && editedContent.hook === "") {
    setEditedContent({
      hook: content.hook,
      body: content.body,
      call_to_action: content.call_to_action,
      hashtags: content.hashtags,
    })
  }

  const handleEdit = () => {
    setIsEditing(true)
  }

  const handleSave = () => {
    // TODO: Implement content update API call
    setIsEditing(false)
  }

  const handleCancel = () => {
    if (content) {
      setEditedContent({
        hook: content.hook,
        body: content.body,
        call_to_action: content.call_to_action,
        hashtags: content.hashtags,
      })
    }
    setIsEditing(false)
  }

  const handleApprove = () => {
    approveContentMutation.mutate()
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this content? This action cannot be undone.')) {
      deleteContentMutation.mutate()
    }
  }

  const generateFullPost = () => {
    return `${editedContent.hook}\n\n${editedContent.body}\n\n${editedContent.call_to_action}\n\n${editedContent.hashtags}`
  }

  const calculateCharacterCount = () => {
    return generateFullPost().length
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !content) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <Card>
            <CardContent className="text-center py-12">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Content not found</h3>
              <p className="text-gray-500 mb-4">The content you're looking for doesn't exist or has been deleted.</p>
              <Link href="/dashboard/content">
                <Button>Back to Content</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <Link 
              href="/dashboard/content" 
              className="inline-flex items-center text-sm text-blue-600 hover:text-blue-500 mb-4"
            >
              <ArrowLeft className="mr-1 h-4 w-4" />
              Back to Content
            </Link>
            
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-2xl font-bold text-gray-900 truncate">
                    {content.topic}
                  </h1>
                  <Badge variant="outline">
                    {content.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Badge>
                  <Badge 
                    className={
                      content.status === 'draft' ? 'bg-gray-100 text-gray-800' :
                      content.status === 'approved' ? 'bg-green-100 text-green-800' :
                      content.status === 'scheduled' ? 'bg-blue-100 text-blue-800' :
                      'bg-purple-100 text-purple-800'
                    }
                  >
                    {content.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Badge>
                </div>
                <p className="text-gray-600">
                  Created on {new Date(content.created_at).toLocaleDateString()} • 
                  Last updated {new Date(content.updated_at).toLocaleDateString()}
                </p>
              </div>
              
              <div className="flex gap-2">
                {!isEditing ? (
                  <>
                    <Button variant="outline" onClick={handleEdit}>
                      <Edit3 className="mr-2 h-4 w-4" />
                      Edit
                    </Button>
                    {content.status === 'draft' && (
                      <Button 
                        onClick={handleApprove}
                        disabled={approveContentMutation.isPending}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Approve
                      </Button>
                    )}
                    <Button variant="outline">
                      <Calendar className="mr-2 h-4 w-4" />
                      Schedule
                    </Button>
                    <Button variant="outline" className="text-red-600 hover:text-red-700">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </Button>
                  </>
                ) : (
                  <>
                    <Button variant="outline" onClick={handleCancel}>
                      <X className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                    <Button onClick={handleSave} className="bg-blue-600 hover:bg-blue-700">
                      <Save className="mr-2 h-4 w-4" />
                      Save Changes
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Content Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Engagement Prediction</p>
                  <p className="text-2xl font-bold text-green-600">
                    {(content.engagement_prediction * 100).toFixed(1)}%
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Characters</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {isEditing ? calculateCharacterCount() : content.character_count}
                  </p>
                </div>
                <Users className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Read Time</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {content.estimated_read_time_seconds}s
                  </p>
                </div>
                <Clock className="h-8 w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Audience</p>
                  <p className="text-sm font-semibold text-orange-600">
                    {content.target_audience.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </p>
                </div>
                <Target className="h-8 w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Content Tabs */}
        <Tabs defaultValue="content" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="content">Content</TabsTrigger>
            <TabsTrigger value="preview">LinkedIn Preview</TabsTrigger>
            <TabsTrigger value="analytics">Performance</TabsTrigger>
          </TabsList>

          {/* Content Editor/Viewer */}
          <TabsContent value="content" className="space-y-6">
            <div className="grid gap-6">
              {/* Hook Section */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Hook</CardTitle>
                  <CardDescription>
                    The attention-grabbing opening that makes people stop scrolling
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isEditing ? (
                    <div className="space-y-2">
                      <Textarea
                        value={editedContent.hook}
                        onChange={(e) => setEditedContent(prev => ({ ...prev, hook: e.target.value }))}
                        className="min-h-[100px] resize-none"
                        placeholder="Enter your hook..."
                      />
                      <div className="text-xs text-gray-500 text-right">
                        {editedContent.hook.length} characters
                      </div>
                    </div>
                  ) : (
                    <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-md">
                      <p className="text-gray-800 whitespace-pre-line">{content.hook}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Body Section */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Body</CardTitle>
                  <CardDescription>
                    The main content that provides value and insights
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isEditing ? (
                    <div className="space-y-2">
                      <Textarea
                        value={editedContent.body}
                        onChange={(e) => setEditedContent(prev => ({ ...prev, body: e.target.value }))}
                        className="min-h-[200px] resize-none"
                        placeholder="Enter your main content..."
                      />
                      <div className="text-xs text-gray-500 text-right">
                        {editedContent.body.length} characters
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 p-4 rounded-md">
                      <p className="text-gray-800 whitespace-pre-line">{content.body}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Call to Action Section */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Call to Action</CardTitle>
                  <CardDescription>
                    The consultation-focused ending that drives inquiries
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isEditing ? (
                    <div className="space-y-2">
                      <Textarea
                        value={editedContent.call_to_action}
                        onChange={(e) => setEditedContent(prev => ({ ...prev, call_to_action: e.target.value }))}
                        className="min-h-[80px] resize-none"
                        placeholder="Enter your call to action..."
                      />
                      <div className="text-xs text-gray-500 text-right">
                        {editedContent.call_to_action.length} characters
                      </div>
                    </div>
                  ) : (
                    <div className="bg-green-50 border-l-4 border-green-400 p-4 rounded-r-md">
                      <p className="text-gray-800 whitespace-pre-line">{content.call_to_action}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Hashtags Section */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Hashtags</CardTitle>
                  <CardDescription>
                    Strategic hashtags for maximum visibility and reach
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isEditing ? (
                    <div className="space-y-2">
                      <Textarea
                        value={editedContent.hashtags}
                        onChange={(e) => setEditedContent(prev => ({ ...prev, hashtags: e.target.value }))}
                        className="min-h-[60px] resize-none"
                        placeholder="Enter hashtags separated by spaces..."
                      />
                      <div className="text-xs text-gray-500 text-right">
                        {editedContent.hashtags.split(' ').filter(tag => tag.length > 0).length} hashtags
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {content.hashtags.split(' ').map((tag, index) => (
                        <Badge key={index} variant="outline" className="text-blue-600">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* LinkedIn Preview */}
          <TabsContent value="preview" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Share2 className="h-5 w-5" />
                  LinkedIn Post Preview
                </CardTitle>
                <CardDescription>
                  How your content will appear on LinkedIn
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-white border border-gray-200 rounded-lg p-6 max-w-lg mx-auto">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                      YN
                    </div>
                    <div>
                      <div className="font-semibold text-gray-900">Your Name</div>
                      <div className="text-sm text-gray-500">Technical Leadership Consultant</div>
                      <div className="text-xs text-gray-400">Now</div>
                    </div>
                  </div>
                  <div className="text-gray-800 whitespace-pre-line leading-relaxed">
                    {isEditing ? generateFullPost() : content.full_post}
                  </div>
                  <div className="flex items-center gap-6 mt-4 pt-4 border-t border-gray-100 text-sm text-gray-500">
                    <button className="flex items-center gap-1 hover:text-blue-600">👍 Like</button>
                    <button className="flex items-center gap-1 hover:text-blue-600">💬 Comment</button>
                    <button className="flex items-center gap-1 hover:text-blue-600">🔄 Repost</button>
                    <button className="flex items-center gap-1 hover:text-blue-600">📤 Send</button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Performance Analytics */}
          <TabsContent value="analytics" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Performance Analytics
                </CardTitle>
                <CardDescription>
                  Content performance metrics and insights
                </CardDescription>
              </CardHeader>
              <CardContent>
                {content.status === 'published' ? (
                  <div className="text-center py-8">
                    <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Analytics Available Soon</h3>
                    <p className="text-gray-500">
                      Performance data will be available 24-48 hours after posting
                    </p>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Performance Predictions</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">
                          {(content.engagement_prediction * 100).toFixed(1)}%
                        </div>
                        <div className="text-sm text-gray-600">Predicted Engagement</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">
                          {Math.round(content.engagement_prediction * 1000)}
                        </div>
                        <div className="text-sm text-gray-600">Expected Interactions</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600">
                          {content.consultation_focused ? '3-5' : '1-2'}
                        </div>
                        <div className="text-sm text-gray-600">Potential Leads</div>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}