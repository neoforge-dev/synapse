"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { format } from "date-fns"
import { 
  ArrowLeft, 
  User, 
  Building, 
  Mail, 
  Phone, 
  Globe,
  MessageSquare,
  Calendar,
  Target,
  TrendingUp,
  DollarSign,
  AlertCircle,
  CheckCircle,
  Clock,
  Star,
  Zap,
  Edit,
  Plus,
  ExternalLink
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

import { leadsApi, LeadDetected } from "@/lib/api-client"
import { LeadScoringVisualization } from "@/components/leads/lead-scoring-visualization"
import { LeadActivityTimeline } from "@/components/leads/lead-activity-timeline"
import { LeadNotesCommunication } from "@/components/leads/lead-notes-communication"

const priorityColors = {
  urgent: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-gray-100 text-gray-800 border-gray-200",
}

const statusColors = {
  pending: "bg-yellow-100 text-yellow-800",
  contacted: "bg-purple-100 text-purple-800",
  qualified: "bg-green-100 text-green-800",
  converted: "bg-emerald-100 text-emerald-800",
  lost: "bg-gray-100 text-gray-800",
}

const inquiryTypeIcons = {
  consultation: "💼",
  project: "🚀",  
  partnership: "🤝",
  other: "💬",
}

export default function LeadDetailPage() {
  const params = useParams()
  const router = useRouter()
  const leadId = params.id as string
  const queryClient = useQueryClient()
  
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false)
  const [conversionDialogOpen, setConversionDialogOpen] = useState(false)
  const [updateForm, setUpdateForm] = useState({
    status: "",
    notes: "",
  })
  const [conversionForm, setConversionForm] = useState({
    consultation_value_euros: "",
    notes: "",
  })

  // Fetch lead data
  const { data: lead, isLoading, error } = useQuery<LeadDetected>({
    queryKey: ['lead', leadId],
    queryFn: () => leadsApi.get(leadId),
  })

  // Update lead mutation
  const updateLeadMutation = useMutation({
    mutationFn: ({ status, notes }: { status: string; notes?: string }) =>
      leadsApi.updateStatus(leadId, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] })
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-analytics'] })
      setUpdateDialogOpen(false)
    },
  })

  // Convert lead mutation
  const convertLeadMutation = useMutation({
    mutationFn: ({ consultation_value_euros, notes }: { consultation_value_euros: number; notes?: string }) =>
      leadsApi.convert(leadId, consultation_value_euros, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] })
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-analytics'] })
      setConversionDialogOpen(false)
    },
  })

  const handleUpdateLead = async () => {
    if (!updateForm.status) return
    await updateLeadMutation.mutateAsync({
      status: updateForm.status,
      notes: updateForm.notes || undefined,
    })
  }

  const handleConvertLead = async () => {
    if (!conversionForm.consultation_value_euros) return
    await convertLeadMutation.mutateAsync({
      consultation_value_euros: parseInt(conversionForm.consultation_value_euros),
      notes: conversionForm.notes || undefined,
    })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 animate-pulse">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="h-8 bg-gray-200 rounded mb-4 w-1/3"></div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <div className="h-64 bg-gray-200 rounded mb-6"></div>
              <div className="h-48 bg-gray-200 rounded"></div>
            </div>
            <div>
              <div className="h-80 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !lead) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Card>
            <CardContent className="text-center py-12">
              <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Lead not found</h3>
              <p className="text-gray-500 mb-4">
                The lead you're looking for doesn't exist or you don't have access to it.
              </p>
              <Button onClick={() => router.push('/dashboard/leads')}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Leads
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return "text-green-600 bg-green-100"
    if (score >= 6) return "text-yellow-600 bg-yellow-100"
    if (score >= 4) return "text-orange-600 bg-orange-100"
    return "text-red-600 bg-red-100"
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "text-green-600"
    if (confidence >= 0.6) return "text-yellow-600"
    return "text-red-600"
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center gap-4">
              <Button 
                variant="ghost" 
                onClick={() => router.push('/dashboard/leads')}
                className="p-2"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                  <span className="text-2xl">
                    {inquiryTypeIcons[lead.inquiry_type as keyof typeof inquiryTypeIcons] || '💬'}
                  </span>
                  {lead.author_name || 'Unknown Contact'}
                </h1>
                <div className="flex items-center gap-2 mt-1">
                  <Badge className={`${priorityColors[lead.priority as keyof typeof priorityColors]}`}>
                    {lead.priority.charAt(0).toUpperCase() + lead.priority.slice(1)} Priority
                  </Badge>
                  <Badge className={`${statusColors[lead.follow_up_status as keyof typeof statusColors]}`}>
                    {lead.follow_up_status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Badge>
                  <Badge variant="outline">
                    {lead.inquiry_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Badge>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Dialog open={updateDialogOpen} onOpenChange={setUpdateDialogOpen}>
                <DialogTrigger asChild>
                  <Button 
                    variant="outline"
                    onClick={() => {
                      setUpdateForm({
                        status: lead.follow_up_status,
                        notes: lead.follow_up_notes || "",
                      })
                    }}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Update Status
                  </Button>
                </DialogTrigger>
              </Dialog>
              
              {lead.follow_up_status !== 'converted' && (
                <Dialog open={conversionDialogOpen} onOpenChange={setConversionDialogOpen}>
                  <DialogTrigger asChild>
                    <Button>
                      <CheckCircle className="mr-2 h-4 w-4" />
                      Mark as Converted
                    </Button>
                  </DialogTrigger>
                </Dialog>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Lead Profile */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Contact Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <Avatar className="h-12 w-12">
                        <AvatarFallback>
                          {(lead.author_name || 'Unknown').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-semibold text-gray-900">
                          {lead.author_name || 'Name not available'}
                        </div>
                        <div className="text-sm text-gray-500">
                          {lead.author_title || 'Title not specified'}
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <Building className="h-4 w-4 text-gray-400" />
                        <span className="text-sm">
                          {lead.author_company || 'Company not specified'}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4 text-gray-400" />
                        <span className="text-sm">
                          {lead.source_platform.charAt(0).toUpperCase() + lead.source_platform.slice(1)}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <div className="text-sm font-medium text-gray-700 mb-1">Company Size</div>
                      <div className="text-sm text-gray-900">
                        {lead.company_size || 'Not specified'}
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-sm font-medium text-gray-700 mb-1">Technical Complexity</div>
                      <div className="text-sm text-gray-900">
                        {lead.technical_complexity || 'Not specified'}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Advanced Lead Scoring */}
            <LeadScoringVisualization lead={lead} />

            {/* Source Content */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  Source Content
                </CardTitle>
                <CardDescription>
                  Content that generated this lead opportunity
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="text-xs">
                      {lead.source_platform.toUpperCase()}
                    </Badge>
                    {lead.source_post_id && (
                      <Badge variant="outline" className="text-xs">
                        Post ID: {lead.source_post_id}
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {lead.content_text || 'Content not available'}
                  </p>
                </div>
                
                {lead.source_post_id && (
                  <div className="mt-4">
                    <Button variant="outline" size="sm">
                      <ExternalLink className="mr-2 h-3 w-3" />
                      View Original Post
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Follow-up Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Follow-up Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <div className="text-sm font-medium text-blue-900 mb-1">
                    Suggested Action
                  </div>
                  <div className="text-sm text-blue-700">
                    {lead.follow_up_suggested || 'No specific suggestion available'}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Button className="w-full" size="sm">
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Send Message
                  </Button>
                  <Button variant="outline" className="w-full" size="sm">
                    <Calendar className="mr-2 h-4 w-4" />
                    Schedule Call
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Activity Timeline */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Quick Timeline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">Lead Detected</div>
                      <div className="text-xs text-gray-500">
                        {format(new Date(lead.detected_at), 'MMM d, yyyy \'at\' h:mm a')}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">Last Updated</div>
                      <div className="text-xs text-gray-500">
                        {format(new Date(lead.updated_at), 'MMM d, yyyy \'at\' h:mm a')}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Advanced Components */}
        <div className="space-y-8 mt-8">
          {/* Activity Timeline */}
          <LeadActivityTimeline lead={lead} />
          
          {/* Notes & Communication */}
          <LeadNotesCommunication lead={lead} />
        </div>
      </div>

      {/* Update Status Dialog */}
      <Dialog open={updateDialogOpen} onOpenChange={setUpdateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Lead Status</DialogTitle>
            <DialogDescription>
              Update the follow-up status and add notes for {lead.author_name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label htmlFor="status">Follow-up Status</Label>
              <Select
                value={updateForm.status}
                onValueChange={(value) => setUpdateForm(prev => ({ ...prev, status: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
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
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={updateForm.notes}
                onChange={(e) => setUpdateForm(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Add follow-up notes or observations..."
                className="min-h-[100px]"
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setUpdateDialogOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleUpdateLead}
                disabled={updateLeadMutation.isPending || !updateForm.status}
              >
                {updateLeadMutation.isPending ? 'Updating...' : 'Update Lead'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Convert Lead Dialog */}
      <Dialog open={conversionDialogOpen} onOpenChange={setConversionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mark Lead as Converted</DialogTitle>
            <DialogDescription>
              Record the consultation value and conversion details for {lead.author_name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label htmlFor="consultation_value">Consultation Value (€)</Label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <input
                  id="consultation_value"
                  type="number"
                  value={conversionForm.consultation_value_euros}
                  onChange={(e) => setConversionForm(prev => ({ ...prev, consultation_value_euros: e.target.value }))}
                  placeholder="5000"
                  className="pl-10 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="conversion_notes">Conversion Notes</Label>
              <Textarea
                id="conversion_notes"
                value={conversionForm.notes}
                onChange={(e) => setConversionForm(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Details about the conversion, consultation type, etc..."
                className="min-h-[100px]"
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setConversionDialogOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleConvertLead}
                disabled={convertLeadMutation.isPending || !conversionForm.consultation_value_euros}
              >
                {convertLeadMutation.isPending ? 'Converting...' : 'Mark as Converted'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}