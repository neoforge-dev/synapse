"use client"

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { 
  Phone,
  Mail,
  MessageSquare,
  Building,
  User,
  DollarSign,
  Target,
  Clock,
  Star,
  ChevronLeft,
  MoreVertical,
  Edit,
  Check,
  AlertCircle,
  TrendingUp,
  Zap,
  ExternalLink
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

import { LeadDetected, leadsApi } from '@/lib/api-client'

interface MobileLeadDetailProps {
  lead: LeadDetected
  isOpen: boolean
  onClose: () => void
}

export function MobileLeadDetail({ lead, isOpen, onClose }: MobileLeadDetailProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'activity' | 'notes'>('overview')
  const [showUpdateDialog, setShowUpdateDialog] = useState(false)
  const [updateForm, setUpdateForm] = useState({
    status: lead.follow_up_status,
    notes: lead.follow_up_notes || ''
  })
  
  const queryClient = useQueryClient()

  const updateLeadMutation = useMutation({
    mutationFn: ({ status, notes }: { status: string; notes?: string }) =>
      leadsApi.updateStatus(lead.id, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead', lead.id] })
      setShowUpdateDialog(false)
    }
  })

  const priorityColors = {
    urgent: "bg-red-100 text-red-800",
    high: "bg-orange-100 text-orange-800", 
    medium: "bg-yellow-100 text-yellow-800",
    low: "bg-gray-100 text-gray-800",
  }

  const statusColors = {
    pending: "bg-yellow-100 text-yellow-800",
    contacted: "bg-purple-100 text-purple-800",
    qualified: "bg-green-100 text-green-800",
    converted: "bg-emerald-100 text-emerald-800",
    lost: "bg-gray-100 text-gray-800",
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return "text-green-600 bg-green-100"
    if (score >= 6) return "text-yellow-600 bg-yellow-100"
    return "text-red-600 bg-red-100"
  }

  const handleUpdateLead = async () => {
    await updateLeadMutation.mutateAsync({
      status: updateForm.status,
      notes: updateForm.notes
    })
  }

  const quickActions = [
    {
      icon: MessageSquare,
      label: 'Message',
      color: 'text-blue-600',
      action: () => console.log('Open message')
    },
    {
      icon: Phone,
      label: 'Call',
      color: 'text-green-600',
      action: () => console.log('Make call')
    },
    {
      icon: Mail,
      label: 'Email',
      color: 'text-purple-600',
      action: () => console.log('Send email')
    },
    {
      icon: ExternalLink,
      label: 'LinkedIn',
      color: 'text-blue-700',
      action: () => console.log('Open LinkedIn')
    }
  ]

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="bottom" className="h-[95vh] p-0">
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
              <h2 className="font-semibold text-gray-900">Lead Details</h2>
              <p className="text-sm text-gray-500">Score: {lead.lead_score}/10</p>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowUpdateDialog(true)}
              className="p-2"
            >
              <Edit className="h-5 w-5" />
            </Button>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b bg-white">
            {[
              { key: 'overview', label: 'Overview' },
              { key: 'activity', label: 'Activity' },
              { key: 'notes', label: 'Notes' }
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <ScrollArea className="flex-1">
            {activeTab === 'overview' && (
              <div className="p-4 space-y-4">
                {/* Contact Info */}
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-4">
                      <Avatar className="h-12 w-12">
                        <AvatarFallback>
                          {(lead.author_name || 'Unknown').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">
                          {lead.author_name || 'Unknown Contact'}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {lead.author_title || 'Title not specified'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 mb-4">
                      <Badge className={priorityColors[lead.priority as keyof typeof priorityColors]}>
                        {lead.priority.charAt(0).toUpperCase() + lead.priority.slice(1)}
                      </Badge>
                      <Badge className={statusColors[lead.follow_up_status as keyof typeof statusColors]}>
                        {lead.follow_up_status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </Badge>
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Building className="h-4 w-4 text-gray-400" />
                        <span>{lead.author_company || 'Company not specified'}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <DollarSign className="h-4 w-4 text-gray-400" />
                        <span>€{lead.estimated_value_euros.toLocaleString()} potential</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-gray-400" />
                        <span>Detected {format(new Date(lead.detected_at), 'MMM d, yyyy')}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Score Analysis */}
                <Card>
                  <CardContent className="p-4">
                    <h4 className="font-medium text-gray-900 mb-3">Lead Score Analysis</h4>
                    
                    <div className="flex items-center gap-4 mb-4">
                      <div className="text-center">
                        <div className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold ${getScoreColor(lead.lead_score)}`}>
                          {lead.lead_score}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Score</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">
                          {Math.round(lead.confidence * 100)}%
                        </div>
                        <div className="text-xs text-gray-500">Confidence</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600">
                          €{lead.estimated_value_euros.toLocaleString()}
                        </div>
                        <div className="text-xs text-gray-500">Est. Value</div>
                      </div>
                    </div>

                    {lead.urgency_indicators && lead.urgency_indicators.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-2">Urgency Signals</div>
                        <div className="flex flex-wrap gap-1">
                          {lead.urgency_indicators.map((indicator, index) => (
                            <Badge key={index} variant="outline" className="text-xs text-orange-600">
                              <Zap className="mr-1 h-3 w-3" />
                              {indicator}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Source Content */}
                <Card>
                  <CardContent className="p-4">
                    <h4 className="font-medium text-gray-900 mb-3">Source Content</h4>
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="text-xs">
                          {lead.source_platform.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-700 leading-relaxed">
                        {lead.content_text || 'Content not available'}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Suggested Actions */}
                {lead.follow_up_suggested && (
                  <Card className="bg-blue-50">
                    <CardContent className="p-4">
                      <div className="flex items-start gap-2">
                        <Target className="h-4 w-4 text-blue-600 mt-1" />
                        <div>
                          <h4 className="font-medium text-blue-900 mb-1">Suggested Action</h4>
                          <p className="text-sm text-blue-700">
                            {lead.follow_up_suggested}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {activeTab === 'activity' && (
              <div className="p-4 space-y-4">
                <div className="text-center py-8 text-gray-500">
                  <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Activity timeline would be rendered here</p>
                  <p className="text-sm mt-1">Integration with activity components</p>
                </div>
              </div>
            )}

            {activeTab === 'notes' && (
              <div className="p-4 space-y-4">
                {lead.follow_up_notes ? (
                  <Card>
                    <CardContent className="p-4">
                      <h4 className="font-medium text-gray-900 mb-2">Latest Notes</h4>
                      <p className="text-sm text-gray-700 leading-relaxed">
                        {lead.follow_up_notes}
                      </p>
                      <div className="text-xs text-gray-500 mt-2">
                        Updated {format(new Date(lead.updated_at), 'MMM d, yyyy')}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Edit className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No notes yet</p>
                    <p className="text-sm mt-1">Tap Edit to add notes</p>
                  </div>
                )}
              </div>
            )}
          </ScrollArea>

          {/* Quick Actions */}
          <div className="p-4 border-t bg-white">
            <div className="grid grid-cols-4 gap-3 mb-3">
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  onClick={action.action}
                  className="flex flex-col items-center gap-2 p-3 bg-gray-50 rounded-lg active:bg-gray-100 transition-colors"
                >
                  <action.icon className={`h-5 w-5 ${action.color}`} />
                  <span className="text-xs font-medium text-gray-700">
                    {action.label}
                  </span>
                </button>
              ))}
            </div>

            <Button
              onClick={() => setShowUpdateDialog(true)}
              className="w-full bg-blue-600 hover:bg-blue-700 h-12 text-base font-medium"
            >
              <Edit className="mr-2 h-5 w-5" />
              Update Status
            </Button>
          </div>
        </div>

        {/* Update Dialog */}
        {showUpdateDialog && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-end">
            <div className="bg-white w-full rounded-t-xl p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">Update Lead</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowUpdateDialog(false)}
                  className="p-2"
                >
                  ×
                </Button>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Follow-up Status
                </label>
                <Select
                  value={updateForm.status}
                  onValueChange={(value) => setUpdateForm(prev => ({ ...prev, status: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="contacted">Contacted</SelectItem>
                    <SelectItem value="qualified">Qualified</SelectItem>
                    <SelectItem value="converted">Converted</SelectItem>
                    <SelectItem value="lost">Lost</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Notes
                </label>
                <Textarea
                  value={updateForm.notes}
                  onChange={(e) => setUpdateForm(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Add follow-up notes..."
                  className="min-h-[80px]"
                />
              </div>

              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={() => setShowUpdateDialog(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleUpdateLead}
                  disabled={updateLeadMutation.isPending}
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                >
                  {updateLeadMutation.isPending ? 'Updating...' : 'Update'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

// Mobile-optimized lead card for lists
export function MobileLeadCard({ lead, onTap }: {
  lead: LeadDetected
  onTap: () => void
}) {
  const priorityColors = {
    urgent: "bg-red-100 text-red-800 border-red-200",
    high: "bg-orange-100 text-orange-800 border-orange-200",
    medium: "bg-yellow-100 text-yellow-800 border-yellow-200", 
    low: "bg-gray-100 text-gray-800 border-gray-200",
  }

  const inquiryTypeIcons = {
    consultation: "💼",
    project: "🚀",
    partnership: "🤝",
    other: "💬",
  }

  return (
    <Card
      className="cursor-pointer active:bg-gray-50 transition-colors"
      onClick={onTap}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="text-xl">
            {inquiryTypeIcons[lead.inquiry_type as keyof typeof inquiryTypeIcons] || '💬'}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-gray-900 truncate">
                {lead.author_name || 'Unknown Contact'}
              </h3>
              <div className="flex items-center gap-1">
                <Star className="h-3 w-3 text-yellow-500 fill-current" />
                <span className="text-xs font-medium">{lead.lead_score}</span>
              </div>
            </div>
            
            <p className="text-sm text-gray-600 mb-2">
              {lead.author_company || 'Company not specified'}
            </p>
            
            <p className="text-sm text-gray-700 line-clamp-2 mb-3 leading-relaxed">
              {lead.content_text?.substring(0, 100) || 'No content preview'}...
            </p>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge className={`text-xs ${priorityColors[lead.priority as keyof typeof priorityColors]}`}>
                  {lead.priority.charAt(0).toUpperCase() + lead.priority.slice(1)}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  €{lead.estimated_value_euros.toLocaleString()}
                </Badge>
              </div>
              
              <div className="text-xs text-gray-500">
                {format(new Date(lead.detected_at), 'MMM d')}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}