"use client"

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { 
  Check, 
  X, 
  Edit, 
  Share2, 
  Calendar, 
  TrendingUp,
  MessageSquare,
  MoreVertical,
  ChevronLeft,
  Clock,
  Zap,
  Target
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'

import { ContentGenerated, contentApi } from '@/lib/api-client'

interface MobileContentApprovalProps {
  content: ContentGenerated
  isOpen: boolean
  onClose: () => void
}

export function MobileContentApproval({ content, isOpen, onClose }: MobileContentApprovalProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const queryClient = useQueryClient()

  const approveMutation = useMutation({
    mutationFn: () => contentApi.approve(content.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
      onClose()
    }
  })

  const getContentTypeIcon = (type: string) => {
    switch (type) {
      case 'linkedin_post':
        return '💼'
      case 'newsletter':
        return '📧'
      case 'blog_post':
        return '📝'
      case 'case_study':
        return '📊'
      default:
        return '📄'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800'
      case 'scheduled':
        return 'bg-blue-100 text-blue-800'
      case 'published':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-yellow-100 text-yellow-800'
    }
  }

  const handleApprove = () => {
    approveMutation.mutate()
  }

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="bottom" className="h-[90vh] p-0">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b bg-white">
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="p-2"
            >
              <ChevronLeft className="h-5 w-5" />
            </Button>
            
            <div className="text-center flex-1">
              <h2 className="font-semibold text-gray-900">Content Review</h2>
              <p className="text-sm text-gray-500">Tap to approve for posting</p>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              className="p-2"
            >
              <MoreVertical className="h-5 w-5" />
            </Button>
          </div>

          {/* Content */}
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-4">
              {/* Content Header */}
              <div className="flex items-start gap-3">
                <div className="text-2xl">
                  {getContentTypeIcon(content.content_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-gray-900 leading-tight">
                    {content.title}
                  </h3>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge className={getStatusColor(content.status)}>
                      {content.status.charAt(0).toUpperCase() + content.status.slice(1)}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {content.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Content Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-blue-600 mx-auto mb-1" />
                  <div className="text-sm font-medium text-blue-900">
                    {content.engagement_prediction || 85}%
                  </div>
                  <div className="text-xs text-blue-700">Engagement</div>
                </div>
                
                <div className="text-center p-3 bg-purple-50 rounded-lg">
                  <Target className="h-5 w-5 text-purple-600 mx-auto mb-1" />
                  <div className="text-sm font-medium text-purple-900">
                    {content.consultation_focused ? 'Yes' : 'No'}
                  </div>
                  <div className="text-xs text-purple-700">Consultation</div>
                </div>
                
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <MessageSquare className="h-5 w-5 text-green-600 mx-auto mb-1" />
                  <div className="text-sm font-medium text-green-900">
                    {content.target_audience || 'Tech Leaders'}
                  </div>
                  <div className="text-xs text-green-700">Audience</div>
                </div>
              </div>

              <Separator />

              {/* Content Preview */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-gray-900">Content Preview</h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="text-xs"
                  >
                    {isExpanded ? 'Show less' : 'Show all'}
                  </Button>
                </div>
                
                <div className={`bg-gray-50 p-4 rounded-lg border-l-4 border-blue-500 ${
                  isExpanded ? '' : 'max-h-48 overflow-hidden'
                }`}>
                  <div className="prose prose-sm max-w-none">
                    {content.content.split('\n').map((paragraph, index) => (
                      <p key={index} className="mb-2 leading-relaxed text-gray-700">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                  
                  {!isExpanded && content.content.length > 200 && (
                    <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-gray-50 to-transparent rounded-b-lg"></div>
                  )}
                </div>
              </div>

              <Separator />

              {/* Publishing Info */}
              <div className="space-y-3">
                <h4 className="font-medium text-gray-900">Publishing Details</h4>
                
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Calendar className="h-4 w-4 text-gray-500" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      {content.scheduled_for ? 'Scheduled for' : 'Will be scheduled'}
                    </div>
                    <div className="text-xs text-gray-600">
                      {content.scheduled_for 
                        ? format(new Date(content.scheduled_for), 'MMM d, yyyy \'at\' h:mm a')
                        : 'Optimal time will be selected automatically'
                      }
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Clock className="h-4 w-4 text-gray-500" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      Created
                    </div>
                    <div className="text-xs text-gray-600">
                      {format(new Date(content.created_at), 'MMM d, yyyy \'at\' h:mm a')}
                    </div>
                  </div>
                </div>
              </div>

              {/* Topic & Context */}
              {content.topic && (
                <>
                  <Separator />
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Topic & Focus</h4>
                    <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
                      <Zap className="h-4 w-4 text-blue-600" />
                      <span className="text-sm text-blue-900 font-medium">
                        {content.topic}
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </ScrollArea>

          {/* Action Buttons */}
          <div className="p-4 border-t bg-white space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Button
                onClick={handleApprove}
                disabled={approveMutation.isPending}
                className="bg-green-600 hover:bg-green-700 text-white h-12 text-base font-medium"
              >
                <Check className="mr-2 h-5 w-5" />
                {approveMutation.isPending ? 'Approving...' : 'Approve & Post'}
              </Button>
              
              <Button
                variant="outline"
                onClick={onClose}
                className="h-12 text-base"
              >
                <Edit className="mr-2 h-5 w-5" />
                Edit First
              </Button>
            </div>
            
            <Button
              variant="ghost"
              onClick={onClose}
              className="w-full h-10 text-sm text-gray-600"
            >
              <X className="mr-2 h-4 w-4" />
              Reject Content
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

// Mobile-optimized content card for lists
export function MobileContentCard({ content, onTap }: { 
  content: ContentGenerated
  onTap: () => void 
}) {
  const getContentTypeIcon = (type: string) => {
    switch (type) {
      case 'linkedin_post':
        return '💼'
      case 'newsletter':
        return '📧'
      case 'blog_post':
        return '📝'
      case 'case_study':
        return '📊'
      default:
        return '📄'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800'
      case 'scheduled':
        return 'bg-blue-100 text-blue-800'
      case 'published':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-yellow-100 text-yellow-800'
    }
  }

  return (
    <Card 
      className="cursor-pointer active:bg-gray-50 transition-colors"
      onClick={onTap}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="text-xl">
            {getContentTypeIcon(content.content_type)}
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-gray-900 leading-tight line-clamp-2 mb-2">
              {content.title}
            </h3>
            
            <p className="text-sm text-gray-600 line-clamp-2 mb-3 leading-relaxed">
              {content.content.substring(0, 120)}...
            </p>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge className={`text-xs ${getStatusColor(content.status)}`}>
                  {content.status.charAt(0).toUpperCase() + content.status.slice(1)}
                </Badge>
                {content.consultation_focused && (
                  <Badge variant="outline" className="text-xs">
                    <Target className="mr-1 h-3 w-3" />
                    Lead Focus
                  </Badge>
                )}
              </div>
              
              <div className="text-xs text-gray-500">
                {format(new Date(content.created_at), 'MMM d')}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}