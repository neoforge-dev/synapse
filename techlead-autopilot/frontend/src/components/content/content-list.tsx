"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { format } from "date-fns"
import { 
  MoreHorizontal, 
  Eye, 
  Edit, 
  CheckCircle, 
  Trash2, 
  Calendar,
  TrendingUp,
  Users,
  Clock,
  Search,
  Filter
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

import { contentApi, ContentGenerated } from "@/lib/api-client"

interface ContentListProps {
  onContentSelect?: (content: ContentGenerated) => void
  className?: string
}

const statusColors = {
  draft: "bg-gray-100 text-gray-800",
  approved: "bg-green-100 text-green-800",
  scheduled: "bg-blue-100 text-blue-800",
  published: "bg-purple-100 text-purple-800",
}

const contentTypeIcons = {
  technical_insight: "💡",
  leadership_story: "👥",
  controversial_take: "⚡",
  career_advice: "📈",
  nobuild_philosophy: "🏗️",
  architecture_review: "🔍",
  team_building: "🧩",
  startup_scaling: "🚀",
}

export function ContentList({ onContentSelect, className }: ContentListProps) {
  const [filters, setFilters] = useState({
    status: "",
    content_type: "",
    search: "",
  })
  const [page, setPage] = useState(1)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  
  const queryClient = useQueryClient()
  const pageSize = 12

  const { data: contentData, isLoading, error } = useQuery({
    queryKey: ['content', filters, page],
    queryFn: () => contentApi.list({
      status: filters.status || undefined,
      content_type: filters.content_type || undefined,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    }),
  })

  const approveContentMutation = useMutation({
    mutationFn: (contentId: string) => contentApi.approve(contentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
    },
  })

  const deleteContentMutation = useMutation({
    mutationFn: (contentId: string) => contentApi.delete(contentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
    },
  })

  const handleApprove = (contentId: string) => {
    approveContentMutation.mutate(contentId)
  }

  const handleDelete = (contentId: string) => {
    if (confirm('Are you sure you want to delete this content?')) {
      deleteContentMutation.mutate(contentId)
    }
  }

  const filteredContent = contentData?.content.filter(content => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      return (
        content.topic.toLowerCase().includes(searchLower) ||
        content.content_type.toLowerCase().includes(searchLower) ||
        content.hook.toLowerCase().includes(searchLower)
      )
    }
    return true
  }) || []

  const totalPages = Math.ceil((contentData?.total || 0) / pageSize)

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(6)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader>
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2"></div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="h-3 bg-gray-200 rounded"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="text-center py-8">
          <p className="text-red-600">Failed to load content</p>
          <p className="text-sm text-gray-500 mt-1">Please try again later</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={className}>
      {/* Filters and Search */}
      <div className="mb-6 space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search content by topic, type, or hook..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="pl-10"
            />
          </div>
          
          <Select
            value={filters.status}
            onValueChange={(value) => setFilters(prev => ({ ...prev, status: value }))}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Status</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
              <SelectItem value="published">Published</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.content_type}
            onValueChange={(value) => setFilters(prev => ({ ...prev, content_type: value }))}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Types</SelectItem>
              <SelectItem value="technical_insight">Technical Insight</SelectItem>
              <SelectItem value="leadership_story">Leadership Story</SelectItem>
              <SelectItem value="controversial_take">Controversial Take</SelectItem>
              <SelectItem value="career_advice">Career Advice</SelectItem>
              <SelectItem value="nobuild_philosophy">NoBuild Philosophy</SelectItem>
              <SelectItem value="architecture_review">Architecture Review</SelectItem>
              <SelectItem value="team_building">Team Building</SelectItem>
              <SelectItem value="startup_scaling">Startup Scaling</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex gap-2">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('grid')}
            >
              Grid
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              List
            </Button>
          </div>
        </div>

        {/* Active Filters */}
        {(filters.status || filters.content_type || filters.search) && (
          <div className="flex flex-wrap gap-2">
            {filters.status && (
              <Badge variant="secondary" className="cursor-pointer" onClick={() => setFilters(prev => ({ ...prev, status: '' }))}>
                Status: {filters.status} ×
              </Badge>
            )}
            {filters.content_type && (
              <Badge variant="secondary" className="cursor-pointer" onClick={() => setFilters(prev => ({ ...prev, content_type: '' }))}>
                Type: {filters.content_type.replace('_', ' ')} ×
              </Badge>
            )}
            {filters.search && (
              <Badge variant="secondary" className="cursor-pointer" onClick={() => setFilters(prev => ({ ...prev, search: '' }))}>
                Search: "{filters.search}" ×
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFilters({ status: '', content_type: '', search: '' })}
            >
              Clear all
            </Button>
          </div>
        )}
      </div>

      {/* Content Grid/List */}
      {filteredContent.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <Filter className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No content found</h3>
            <p className="text-gray-500 mb-4">
              {filters.search || filters.status || filters.content_type
                ? "Try adjusting your filters or search terms"
                : "Start by generating your first piece of content"
              }
            </p>
            <Button onClick={() => window.location.href = '/dashboard/content/generate'}>
              Generate Content
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className={`grid gap-4 ${viewMode === 'grid' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}`}>
            {filteredContent.map((content) => (
              <Card key={content.id} className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">
                          {contentTypeIcons[content.content_type as keyof typeof contentTypeIcons] || '📝'}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {content.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </Badge>
                        <Badge className={`text-xs ${statusColors[content.status as keyof typeof statusColors]}`}>
                          {content.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </Badge>
                      </div>
                      <CardTitle className="text-base line-clamp-2">
                        {content.topic}
                      </CardTitle>
                      <CardDescription className="line-clamp-2">
                        {content.hook}
                      </CardDescription>
                    </div>
                    
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => onContentSelect?.(content)}>
                          <Eye className="mr-2 h-4 w-4" />
                          View
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Edit className="mr-2 h-4 w-4" />
                          Edit
                        </DropdownMenuItem>
                        {content.status === 'draft' && (
                          <DropdownMenuItem onClick={() => handleApprove(content.id)}>
                            <CheckCircle className="mr-2 h-4 w-4" />
                            Approve
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem>
                          <Calendar className="mr-2 h-4 w-4" />
                          Schedule
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          onClick={() => handleDelete(content.id)}
                          className="text-red-600"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                
                <CardContent className="pt-0">
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3 text-gray-400" />
                      <span className="text-gray-600">{(content.engagement_prediction * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Users className="h-3 w-3 text-gray-400" />
                      <span className="text-gray-600">{content.character_count}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-gray-400" />
                      <span className="text-gray-600">{content.estimated_read_time_seconds}s</span>
                    </div>
                  </div>
                  
                  <div className="mt-3 text-xs text-gray-500">
                    Created {format(new Date(content.created_at), 'MMM d, yyyy')}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, contentData?.total || 0)} of {contentData?.total || 0} results
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(prev => Math.max(1, prev - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <div className="flex gap-1">
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
                    const pageNum = Math.max(1, Math.min(totalPages - 4, page - 2)) + i
                    return (
                      <Button
                        key={pageNum}
                        variant={pageNum === page ? "default" : "outline"}
                        size="sm"
                        onClick={() => setPage(pageNum)}
                        className="w-8"
                      >
                        {pageNum}
                      </Button>
                    )
                  })}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}