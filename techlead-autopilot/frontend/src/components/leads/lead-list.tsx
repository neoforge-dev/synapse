"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { format } from "date-fns"
import Link from "next/link"
import { 
  MoreHorizontal, 
  Eye, 
  MessageSquare, 
  CheckCircle, 
  X,
  Search,
  Filter,
  Calendar,
  Building,
  User,
  DollarSign,
  TrendingUp,
  Clock,
  ArrowUpRight
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

import { leadsApi, LeadDetected, LeadListResponse } from "@/lib/api-client"

interface LeadListProps {
  filterStatus?: string
  className?: string
}

const priorityColors = {
  urgent: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-gray-100 text-gray-800 border-gray-200",
}

const statusColors = {
  new: "bg-blue-100 text-blue-800",
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

export function LeadList({ filterStatus, className }: LeadListProps) {
  const [filters, setFilters] = useState({
    priority: "",
    inquiry_type: "",
    follow_up_status: filterStatus || "",
    search: "",
    days: "",
  })
  const [page, setPage] = useState(1)
  const [selectedLead, setSelectedLead] = useState<LeadDetected | null>(null)
  const [isUpdating, setIsUpdating] = useState(false)
  const [updateForm, setUpdateForm] = useState({
    status: "",
    notes: "",
  })
  
  const queryClient = useQueryClient()
  const pageSize = 12

  const { data: leadsData, isLoading, error } = useQuery<LeadListResponse>({
    queryKey: ['leads', filters, page],
    queryFn: () => leadsApi.list({
      priority: filters.priority || undefined,
      inquiry_type: filters.inquiry_type || undefined,
      follow_up_status: filters.follow_up_status || undefined,
      days: filters.days ? parseInt(filters.days) : undefined,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    }),
  })

  const updateLeadMutation = useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: string; notes?: string }) =>
      leadsApi.updateStatus(id, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-analytics'] })
      setSelectedLead(null)
      setIsUpdating(false)
    },
  })

  const handleUpdateLead = async () => {
    if (!selectedLead || !updateForm.status) return

    setIsUpdating(true)
    try {
      await updateLeadMutation.mutateAsync({
        id: selectedLead.id,
        status: updateForm.status,
        notes: updateForm.notes,
      })
    } catch (error) {
      console.error('Failed to update lead:', error)
      setIsUpdating(false)
    }
  }

  const filteredLeads = leadsData?.leads || []

  const totalPages = Math.ceil((leadsData?.total || 0) / pageSize)

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
          <p className="text-red-600">Failed to load leads</p>
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
              placeholder="Search by contact name, company, or content..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="pl-10"
            />
          </div>
          
          <Select
            value={filters.priority}
            onValueChange={(value) => setFilters(prev => ({ ...prev, priority: value }))}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All Priorities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Priorities</SelectItem>
              <SelectItem value="urgent">Urgent</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.inquiry_type}
            onValueChange={(value) => setFilters(prev => ({ ...prev, inquiry_type: value }))}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Types</SelectItem>
              <SelectItem value="consultation">Consultation</SelectItem>
              <SelectItem value="project">Project</SelectItem>
              <SelectItem value="partnership">Partnership</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>

          {!filterStatus && (
            <Select
              value={filters.follow_up_status}
              onValueChange={(value) => setFilters(prev => ({ ...prev, follow_up_status: value }))}
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="contacted">Contacted</SelectItem>
                <SelectItem value="qualified">Qualified</SelectItem>
                <SelectItem value="converted">Converted</SelectItem>
                <SelectItem value="lost">Lost</SelectItem>
              </SelectContent>
            </Select>
          )}

          <Select
            value={filters.days}
            onValueChange={(value) => setFilters(prev => ({ ...prev, days: value }))}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All Time" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Time</SelectItem>
              <SelectItem value="1">Last 24h</SelectItem>
              <SelectItem value="7">Last Week</SelectItem>
              <SelectItem value="30">Last Month</SelectItem>
              <SelectItem value="90">Last Quarter</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Active Filters */}
        {(filters.priority || filters.inquiry_type || filters.follow_up_status || filters.days || filters.search) && (
          <div className="flex flex-wrap gap-2">
            {filters.priority && (
              <Badge variant="secondary" className="cursor-pointer" onClick={() => setFilters(prev => ({ ...prev, priority: '' }))}>
                Priority: {filters.priority} ×
              </Badge>
            )}
            {filters.inquiry_type && (
              <Badge variant="secondary" className="cursor-pointer" onClick={() => setFilters(prev => ({ ...prev, inquiry_type: '' }))}>
                Type: {filters.inquiry_type} ×
              </Badge>
            )}
            {filters.follow_up_status && (
              <Badge variant="secondary" className="cursor-pointer" onClick={() => setFilters(prev => ({ ...prev, follow_up_status: '' }))}>
                Status: {filters.follow_up_status} ×
              </Badge>
            )}
            {filters.days && (
              <Badge variant="secondary" className="cursor-pointer" onClick={() => setFilters(prev => ({ ...prev, days: '' }))}>
                Last {filters.days} days ×
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
              onClick={() => setFilters({ priority: '', inquiry_type: '', follow_up_status: filterStatus || '', search: '', days: '' })}
            >
              Clear all
            </Button>
          </div>
        )}
      </div>

      {/* Lead Cards */}
      {filteredLeads.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <Filter className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No leads found</h3>
            <p className="text-gray-500 mb-4">
              {filters.search || filters.priority || filters.inquiry_type || filters.follow_up_status || filters.days
                ? "Try adjusting your filters or search terms"
                : "Leads will appear here as they're detected from your LinkedIn content"
              }
            </p>
            <Link href="/dashboard/content/generate">
              <Button>Generate Content to Attract Leads</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4">
            {filteredLeads.map((lead: any) => (
              <Card key={lead.id} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-2xl">
                          {inquiryTypeIcons[lead.inquiry_type as keyof typeof inquiryTypeIcons] || '💬'}
                        </span>
                        <div>
                          <h3 className="font-semibold text-gray-900 text-lg">
                            {lead.author_name || 'Unknown Contact'}
                          </h3>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              {lead.inquiry_type.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                            </Badge>
                            <Badge className={`text-xs ${priorityColors[lead.priority as keyof typeof priorityColors]}`}>
                              {lead.priority.charAt(0).toUpperCase() + lead.priority.slice(1)}
                            </Badge>
                            <Badge className={`text-xs ${statusColors[lead.follow_up_status as keyof typeof statusColors]}`}>
                              {lead.follow_up_status.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                        <div className="flex items-center gap-2">
                          <Building className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600">
                            {lead.author_company || 'Company not specified'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600">
                            {lead.author_title || 'Title not specified'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <DollarSign className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600">
                            €{lead.estimated_value_euros?.toLocaleString() || '0'} potential
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <TrendingUp className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600">
                            Score: {lead.lead_score}/10 ({Math.round((lead.confidence || 0) * 100)}%)
                          </span>
                        </div>
                      </div>

                      <div className="bg-gray-50 p-3 rounded-lg mb-4">
                        <p className="text-sm text-gray-700 line-clamp-2">
                          {lead.content_text || 'No content available'}
                        </p>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Detected {format(new Date(lead.detected_at), 'MMM d, yyyy')}
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          Updated {format(new Date(lead.updated_at), 'MMM d, yyyy')}
                        </div>
                        {lead.urgency_indicators && lead.urgency_indicators.length > 0 && (
                          <div className="flex items-center gap-1">
                            <span className="text-orange-600">⚡ {lead.urgency_indicators.length} urgency signal(s)</span>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex flex-col gap-2 ml-4">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link href={`/dashboard/leads/${lead.id}`} className="flex items-center">
                              <Eye className="mr-2 h-4 w-4" />
                              View Details
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => {
                              setSelectedLead(lead)
                              setUpdateForm({ status: lead.follow_up_status, notes: lead.follow_up_notes || '' })
                            }}
                          >
                            <CheckCircle className="mr-2 h-4 w-4" />
                            Update Status
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <MessageSquare className="mr-2 h-4 w-4" />
                            Contact Lead
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-red-600">
                            <X className="mr-2 h-4 w-4" />
                            Mark as Lost
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      
                      <Link href={`/dashboard/leads/${lead.id}`}>
                        <Button size="sm" variant="outline">
                          <ArrowUpRight className="h-3 w-3" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, leadsData?.total || 0)} of {leadsData?.total || 0} results
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

      {/* Update Lead Dialog */}
      <Dialog open={!!selectedLead} onOpenChange={() => setSelectedLead(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Lead Status</DialogTitle>
            <DialogDescription>
              Update the follow-up status and add notes for {selectedLead?.author_name}
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
              <Button variant="outline" onClick={() => setSelectedLead(null)}>
                Cancel
              </Button>
              <Button 
                onClick={handleUpdateLead}
                disabled={isUpdating || !updateForm.status}
              >
                {isUpdating ? 'Updating...' : 'Update Lead'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}