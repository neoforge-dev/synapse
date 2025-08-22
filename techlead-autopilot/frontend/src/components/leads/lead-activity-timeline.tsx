"use client"

import { useState } from "react"
import { format, formatDistanceToNow } from "date-fns"
import { 
  Calendar,
  MessageSquare, 
  Phone,
  Mail,
  CheckCircle,
  Clock,
  AlertCircle,
  User,
  Target,
  TrendingUp,
  Plus,
  Edit,
  ExternalLink,
  Bot,
  UserCheck,
  Zap
} from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

import { LeadDetected } from "@/lib/api-client"

interface ActivityEvent {
  id: string
  type: 'detection' | 'status_change' | 'note_added' | 'contact_attempt' | 'meeting_scheduled' | 'follow_up_due' | 'system_event'
  title: string
  description: string
  timestamp: string
  icon: React.ComponentType<any>
  color: string
  bgColor: string
  actor?: string
  metadata?: Record<string, any>
}

interface LeadActivityTimelineProps {
  lead: LeadDetected
  className?: string
}

export function LeadActivityTimeline({ lead, className }: LeadActivityTimelineProps) {
  const [newEventDialogOpen, setNewEventDialogOpen] = useState(false)
  const [newEventForm, setNewEventForm] = useState({
    type: '',
    title: '',
    description: '',
    scheduled_for: '',
  })

  // Generate timeline events from lead data
  const timelineEvents: ActivityEvent[] = [
    // Lead detection event
    {
      id: 'detection',
      type: 'detection',
      title: 'Lead Detected',
      description: `AI detected consultation opportunity from ${lead.source_platform} with ${Math.round(lead.confidence * 100)}% confidence`,
      timestamp: lead.detected_at,
      icon: Bot,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      actor: 'TechLead AutoPilot AI',
      metadata: {
        source: lead.source_platform,
        confidence: lead.confidence,
        score: lead.lead_score
      }
    },

    // Status change events (simulated based on current status)
    ...(lead.follow_up_status !== 'pending' ? [{
      id: 'status_contacted',
      type: 'status_change' as const,
      title: 'Status Updated to Contacted',
      description: 'Initial contact made with prospect',
      timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
      icon: MessageSquare,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      actor: 'System User'
    }] : []),

    ...(lead.follow_up_status === 'qualified' || lead.follow_up_status === 'converted' ? [{
      id: 'status_qualified',
      type: 'status_change' as const,
      title: 'Lead Qualified',
      description: 'Prospect meets qualification criteria and shows genuine interest',
      timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
      icon: Target,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      actor: 'System User'
    }] : []),

    ...(lead.follow_up_status === 'converted' ? [{
      id: 'status_converted',
      type: 'status_change' as const,
      title: 'Lead Converted!',
      description: `Successfully converted to consultation worth €${lead.estimated_value_euros.toLocaleString()}`,
      timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(), // 12 hours ago
      icon: CheckCircle,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-100',
      actor: 'System User',
      metadata: {
        value: lead.estimated_value_euros
      }
    }] : []),

    // Follow-up notes events
    ...(lead.follow_up_notes ? [{
      id: 'notes_added',
      type: 'note_added' as const,
      title: 'Notes Added',
      description: lead.follow_up_notes,
      timestamp: lead.updated_at,
      icon: Edit,
      color: 'text-gray-600',
      bgColor: 'bg-gray-100',
      actor: 'System User'
    }] : []),

    // Urgency indicators as system events
    ...(lead.urgency_indicators?.map((indicator, index) => ({
      id: `urgency_${index}`,
      type: 'system_event' as const,
      title: 'Urgency Signal Detected',
      description: `AI identified urgency indicator: "${indicator}"`,
      timestamp: new Date(new Date(lead.detected_at).getTime() + index * 60 * 1000).toISOString(),
      icon: Zap,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      actor: 'TechLead AutoPilot AI',
      metadata: {
        indicator
      }
    })) || [])
  ].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

  // Generate suggested follow-up actions
  const suggestedActions = getSuggestedActions(lead)

  const handleAddEvent = () => {
    // In a real implementation, this would call an API
    console.log('Adding event:', newEventForm)
    setNewEventDialogOpen(false)
    setNewEventForm({ type: '', title: '', description: '', scheduled_for: '' })
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Timeline Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Activity Timeline
              </CardTitle>
              <CardDescription>
                Complete interaction history and follow-up tracking
              </CardDescription>
            </div>
            <Dialog open={newEventDialogOpen} onOpenChange={setNewEventDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Activity
                </Button>
              </DialogTrigger>
            </Dialog>
          </div>
        </CardHeader>
      </Card>

      {/* Suggested Actions */}
      <Card className="border-blue-200 bg-blue-50">
        <CardHeader>
          <CardTitle className="text-blue-900 flex items-center gap-2">
            <Target className="h-4 w-4" />
            Suggested Next Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {suggestedActions.map((action, index) => (
              <div key={index} className="flex items-center gap-3 p-3 bg-white rounded-lg border">
                <action.icon className={`h-4 w-4 ${action.color}`} />
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">{action.title}</div>
                  <div className="text-xs text-gray-500">{action.description}</div>
                </div>
                <Button size="sm" variant="outline">
                  {action.buttonText}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Timeline Events */}
      <Card>
        <CardHeader>
          <CardTitle>Complete Activity History</CardTitle>
          <CardDescription>
            Chronological view of all interactions and system events
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200"></div>
            
            <div className="space-y-6">
              {timelineEvents.map((event, index) => {
                const Icon = event.icon
                const isRecent = new Date(event.timestamp).getTime() > Date.now() - 24 * 60 * 60 * 1000
                
                return (
                  <div key={event.id} className="relative flex items-start gap-4">
                    {/* Timeline marker */}
                    <div className={`relative z-10 p-2 rounded-full ${event.bgColor} border-4 border-white shadow-sm`}>
                      <Icon className={`h-4 w-4 ${event.color}`} />
                    </div>
                    
                    {/* Event content */}
                    <div className="flex-1 min-w-0 pb-6">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-sm font-medium text-gray-900">{event.title}</h3>
                        {isRecent && (
                          <Badge variant="secondary" className="text-xs">
                            Recent
                          </Badge>
                        )}
                      </div>
                      
                      <p className="text-sm text-gray-600 mb-2">{event.description}</p>
                      
                      {/* Event metadata */}
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {format(new Date(event.timestamp), 'MMM d, yyyy \'at\' h:mm a')}
                        </span>
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {event.actor || 'System'}
                        </span>
                        <span className="text-gray-400">
                          {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                      
                      {/* Additional metadata */}
                      {event.metadata && (
                        <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                          {Object.entries(event.metadata).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-gray-600 capitalize">{key.replace('_', ' ')}:</span>
                              <span className="font-medium">
                                {typeof value === 'number' ? (
                                  key.includes('value') ? `€${value.toLocaleString()}` : 
                                  key.includes('confidence') ? `${Math.round(value * 100)}%` :
                                  value
                                ) : value}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    {/* Time indicator */}
                    <div className="text-xs text-gray-400 min-w-0">
                      {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Add Activity Dialog */}
      <Dialog open={newEventDialogOpen} onOpenChange={setNewEventDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Timeline Activity</DialogTitle>
            <DialogDescription>
              Record a new interaction or follow-up activity for this lead
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label htmlFor="event_type">Activity Type</Label>
              <Select
                value={newEventForm.type}
                onValueChange={(value) => setNewEventForm(prev => ({ ...prev, type: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select activity type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="contact_attempt">Contact Attempt</SelectItem>
                  <SelectItem value="meeting_scheduled">Meeting Scheduled</SelectItem>
                  <SelectItem value="note_added">Note Added</SelectItem>
                  <SelectItem value="follow_up_due">Follow-up Due</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="event_title">Title</Label>
              <input
                id="event_title"
                type="text"
                value={newEventForm.title}
                onChange={(e) => setNewEventForm(prev => ({ ...prev, title: e.target.value }))}
                placeholder="Brief title for this activity"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <Label htmlFor="event_description">Description</Label>
              <Textarea
                id="event_description"
                value={newEventForm.description}
                onChange={(e) => setNewEventForm(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Detailed description of the activity or outcome..."
                className="min-h-[100px]"
              />
            </div>

            {(newEventForm.type === 'meeting_scheduled' || newEventForm.type === 'follow_up_due') && (
              <div>
                <Label htmlFor="scheduled_for">Scheduled For</Label>
                <input
                  id="scheduled_for"
                  type="datetime-local"
                  value={newEventForm.scheduled_for}
                  onChange={(e) => setNewEventForm(prev => ({ ...prev, scheduled_for: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setNewEventDialogOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleAddEvent}
                disabled={!newEventForm.type || !newEventForm.title}
              >
                Add Activity
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// Helper function to generate suggested actions based on lead data
function getSuggestedActions(lead: LeadDetected) {
  const actions = []
  const hoursAgo = (Date.now() - new Date(lead.detected_at).getTime()) / (1000 * 60 * 60)
  
  // Initial contact suggestion
  if (lead.follow_up_status === 'pending') {
    actions.push({
      title: 'Make Initial Contact',
      description: hoursAgo < 24 ? 'Respond while inquiry is fresh' : 'Follow up on inquiry',
      icon: MessageSquare,
      color: 'text-blue-600',
      buttonText: 'Contact',
      priority: hoursAgo > 48 ? 'high' : 'medium'
    })
  }

  // Call scheduling for contacted leads
  if (lead.follow_up_status === 'contacted') {
    actions.push({
      title: 'Schedule Discovery Call',
      description: 'Book consultation to understand requirements',
      icon: Phone,
      color: 'text-green-600',
      buttonText: 'Schedule',
      priority: 'high'
    })
  }

  // Qualification follow-up
  if (lead.follow_up_status === 'qualified') {
    actions.push({
      title: 'Send Proposal',
      description: 'Provide detailed consultation proposal',
      icon: TrendingUp,
      color: 'text-purple-600',
      buttonText: 'Create',
      priority: 'high'
    })
  }

  // High-value lead prioritization
  if (lead.lead_score >= 8) {
    actions.push({
      title: 'Executive Outreach',
      description: 'High-value lead requires senior attention',
      icon: UserCheck,
      color: 'text-red-600',
      buttonText: 'Escalate',
      priority: 'high'
    })
  }

  // Research suggestion for incomplete data
  if (!lead.author_company || !lead.author_title) {
    actions.push({
      title: 'Research Contact',
      description: 'Gather additional prospect information',
      icon: ExternalLink,
      color: 'text-yellow-600',
      buttonText: 'Research',
      priority: 'medium'
    })
  }

  return actions.slice(0, 4) // Limit to top 4 suggestions
}