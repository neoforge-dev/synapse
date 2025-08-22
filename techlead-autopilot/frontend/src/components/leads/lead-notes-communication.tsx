"use client"

import { useState } from "react"
import { format } from "date-fns"
import { 
  MessageSquare,
  Plus,
  Edit,
  Trash2,
  Mail,
  Phone,
  Calendar,
  ExternalLink,
  User,
  Clock,
  Paperclip,
  Send,
  Star,
  Flag,
  Copy,
  Search
} from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { LeadDetected } from "@/lib/api-client"

interface Note {
  id: string
  content: string
  type: 'note' | 'call' | 'email' | 'meeting' | 'task'
  author: string
  timestamp: string
  important: boolean
  tags: string[]
  attachments?: string[]
}

interface CommunicationTemplate {
  id: string
  name: string
  subject: string
  content: string
  type: 'initial_contact' | 'follow_up' | 'proposal' | 'meeting_request'
}

interface LeadNotesCommunicationProps {
  lead: LeadDetected
  className?: string
}

// Sample communication templates
const communicationTemplates: CommunicationTemplate[] = [
  {
    id: 'initial_contact',
    name: 'Initial Contact Email',
    subject: 'Re: Your LinkedIn inquiry about tech leadership consultation',
    type: 'initial_contact',
    content: `Hi {{contact_name}},

Thank you for reaching out regarding technical leadership consultation. I noticed your inquiry on LinkedIn and would love to learn more about the challenges you're facing at {{company_name}}.

Based on your message, it sounds like you might benefit from our expertise in:
- Technical strategy and architecture
- Team scaling and leadership
- Engineering process optimization

Would you be available for a brief 15-minute call this week to discuss your specific needs? I have availability on:
- Tuesday at 2 PM
- Wednesday at 10 AM
- Thursday at 4 PM

Looking forward to connecting!

Best regards,
[Your Name]`
  },
  {
    id: 'follow_up',
    name: 'Follow-up Email',
    subject: 'Following up on your consultation inquiry',
    type: 'follow_up',
    content: `Hi {{contact_name}},

I wanted to follow up on my previous email regarding technical leadership consultation for {{company_name}}.

I understand that priorities can shift quickly in a technical leadership role. If the timing isn't right now, I'd be happy to connect at a more convenient time.

Alternatively, I could share some relevant resources that might be immediately helpful:
- Our guide on "Scaling Engineering Teams"
- Recent case study with a similar company in your industry
- Framework for technical decision-making

Would any of these be valuable? Just let me know.

Best regards,
[Your Name]`
  },
  {
    id: 'proposal',
    name: 'Proposal Follow-up',
    subject: 'Consultation proposal for {{company_name}}',
    type: 'proposal',
    content: `Hi {{contact_name}},

Thank you for taking the time to discuss your technical leadership challenges yesterday. Based on our conversation, I've prepared a customized consultation proposal.

The engagement would focus on:
1. {{specific_need_1}}
2. {{specific_need_2}}
3. {{specific_need_3}}

Timeline: {{timeline}}
Investment: {{budget}}

I've attached the detailed proposal for your review. I'm happy to discuss any questions or modifications you might have.

When would be a good time to review this together?

Best regards,
[Your Name]`
  }
]

export function LeadNotesCommunication({ lead, className }: LeadNotesCommunicationProps) {
  const [activeTab, setActiveTab] = useState("notes")
  const [newNoteDialogOpen, setNewNoteDialogOpen] = useState(false)
  const [emailDialogOpen, setEmailDialogOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")

  // Sample notes data (in real app, this would come from API)
  const [notes] = useState<Note[]>([
    {
      id: '1',
      content: lead.follow_up_notes || 'Initial AI-detected consultation inquiry. High-quality lead with strong indicators.',
      type: 'note',
      author: 'TechLead AutoPilot AI',
      timestamp: lead.detected_at,
      important: true,
      tags: ['ai-detection', 'high-priority']
    },
    {
      id: '2',
      content: 'Researched company background. Series B startup with 50+ engineers. Good fit for our technical leadership consulting.',
      type: 'note',
      author: 'System User',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      important: false,
      tags: ['research', 'company-analysis']
    }
  ])

  const [newNote, setNewNote] = useState({
    content: '',
    type: 'note' as Note['type'],
    important: false,
    tags: ''
  })

  const [emailComposer, setEmailComposer] = useState({
    template: '',
    subject: '',
    content: '',
    to: lead.author_name ? `${lead.author_name} <email@${lead.author_company?.toLowerCase().replace(/\s+/g, '')}.com>` : ''
  })

  const handleAddNote = () => {
    // In real implementation, this would call an API
    console.log('Adding note:', newNote)
    setNewNoteDialogOpen(false)
    setNewNote({ content: '', type: 'note', important: false, tags: '' })
  }

  const handleSendEmail = () => {
    // In real implementation, this would send email via API
    console.log('Sending email:', emailComposer)
    setEmailDialogOpen(false)
  }

  const applyTemplate = (templateId: string) => {
    const template = communicationTemplates.find(t => t.id === templateId)
    if (template) {
      let content = template.content
        .replace(/{{contact_name}}/g, lead.author_name || '[Name]')
        .replace(/{{company_name}}/g, lead.author_company || '[Company]')
      
      setEmailComposer(prev => ({
        ...prev,
        template: templateId,
        subject: template.subject
          .replace(/{{contact_name}}/g, lead.author_name || '[Name]')
          .replace(/{{company_name}}/g, lead.author_company || '[Company]'),
        content
      }))
    }
  }

  const filteredNotes = notes.filter(note => 
    searchQuery === '' || 
    note.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    note.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const getTypeIcon = (type: Note['type']) => {
    switch (type) {
      case 'call': return Phone
      case 'email': return Mail
      case 'meeting': return Calendar
      case 'task': return Flag
      default: return MessageSquare
    }
  }

  const getTypeColor = (type: Note['type']) => {
    switch (type) {
      case 'call': return 'text-green-600 bg-green-100'
      case 'email': return 'text-blue-600 bg-blue-100'
      case 'meeting': return 'text-purple-600 bg-purple-100'
      case 'task': return 'text-orange-600 bg-orange-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Notes & Communication
          </CardTitle>
          <CardDescription>
            Manage all interactions, notes, and communications with this lead
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="notes">Notes & Timeline</TabsTrigger>
              <TabsTrigger value="communication">Communication</TabsTrigger>
              <TabsTrigger value="templates">Templates</TabsTrigger>
            </TabsList>

            {/* Notes Tab */}
            <TabsContent value="notes" className="space-y-4">
              {/* Search and Add Controls */}
              <div className="flex items-center gap-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    placeholder="Search notes and activities..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
                
                <Dialog open={newNoteDialogOpen} onOpenChange={setNewNoteDialogOpen}>
                  <DialogTrigger asChild>
                    <Button size="sm">
                      <Plus className="mr-2 h-4 w-4" />
                      Add Note
                    </Button>
                  </DialogTrigger>
                </Dialog>
              </div>

              {/* Notes List */}
              <div className="space-y-4">
                {filteredNotes.map((note) => {
                  const TypeIcon = getTypeIcon(note.type)
                  
                  return (
                    <Card key={note.id} className={`${note.important ? 'ring-2 ring-yellow-200' : ''}`}>
                      <CardContent className="p-4">
                        <div className="flex items-start gap-4">
                          <div className={`p-2 rounded-full ${getTypeColor(note.type)}`}>
                            <TypeIcon className="h-4 w-4" />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant="outline" className="text-xs">
                                {note.type.replace('_', ' ').toUpperCase()}
                              </Badge>
                              {note.important && (
                                <Badge variant="secondary" className="text-xs">
                                  <Star className="mr-1 h-3 w-3" />
                                  Important
                                </Badge>
                              )}
                              <div className="flex items-center gap-1 text-xs text-gray-500">
                                <User className="h-3 w-3" />
                                {note.author}
                              </div>
                            </div>
                            
                            <p className="text-sm text-gray-900 mb-3 leading-relaxed">
                              {note.content}
                            </p>
                            
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                {note.tags.map((tag, index) => (
                                  <Badge key={index} variant="outline" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                              
                              <div className="flex items-center gap-2 text-xs text-gray-500">
                                <Clock className="h-3 w-3" />
                                {format(new Date(note.timestamp), 'MMM d, yyyy \'at\' h:mm a')}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm">
                              <Edit className="h-3 w-3" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </TabsContent>

            {/* Communication Tab */}
            <TabsContent value="communication" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Dialog open={emailDialogOpen} onOpenChange={setEmailDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" className="h-20 flex flex-col items-center justify-center">
                      <Mail className="h-6 w-6 mb-2" />
                      <span>Send Email</span>
                    </Button>
                  </DialogTrigger>
                </Dialog>
                
                <Button variant="outline" className="h-20 flex flex-col items-center justify-center">
                  <Phone className="h-6 w-6 mb-2" />
                  <span>Make Call</span>
                </Button>
                
                <Button variant="outline" className="h-20 flex flex-col items-center justify-center">
                  <Calendar className="h-6 w-6 mb-2" />
                  <span>Schedule Meeting</span>
                </Button>
              </div>

              {/* Quick Actions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Quick Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <div className="font-medium">LinkedIn Message</div>
                      <div className="text-sm text-gray-500">Reply to original inquiry</div>
                    </div>
                    <Button size="sm" variant="outline">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Open LinkedIn
                    </Button>
                  </div>
                  
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <div className="font-medium">Company Research</div>
                      <div className="text-sm text-gray-500">Gather more background info</div>
                    </div>
                    <Button size="sm" variant="outline">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Research
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Templates Tab */}
            <TabsContent value="templates" className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                {communicationTemplates.map((template) => (
                  <Card key={template.id} className="cursor-pointer hover:shadow-md transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900 mb-1">{template.name}</h3>
                          <p className="text-sm text-gray-600 mb-2">Subject: {template.subject}</p>
                          <div className="text-xs text-gray-500 line-clamp-3">
                            {template.content.substring(0, 200)}...
                          </div>
                        </div>
                        <div className="flex gap-2 ml-4">
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => {
                              applyTemplate(template.id)
                              setEmailDialogOpen(true)
                            }}
                          >
                            Use Template
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Add Note Dialog */}
      <Dialog open={newNoteDialogOpen} onOpenChange={setNewNoteDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add New Note</DialogTitle>
            <DialogDescription>
              Record important information, calls, or interactions with this lead
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="note_type">Note Type</Label>
                <Select
                  value={newNote.type}
                  onValueChange={(value: Note['type']) => setNewNote(prev => ({ ...prev, type: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="note">General Note</SelectItem>
                    <SelectItem value="call">Phone Call</SelectItem>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="meeting">Meeting</SelectItem>
                    <SelectItem value="task">Task/Reminder</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  id="important"
                  type="checkbox"
                  checked={newNote.important}
                  onChange={(e) => setNewNote(prev => ({ ...prev, important: e.target.checked }))}
                  className="rounded"
                />
                <Label htmlFor="important" className="text-sm">Mark as important</Label>
              </div>
            </div>

            <div>
              <Label htmlFor="note_content">Content</Label>
              <Textarea
                id="note_content"
                value={newNote.content}
                onChange={(e) => setNewNote(prev => ({ ...prev, content: e.target.value }))}
                placeholder="Enter your note here..."
                className="min-h-[120px]"
              />
            </div>

            <div>
              <Label htmlFor="note_tags">Tags</Label>
              <Input
                id="note_tags"
                value={newNote.tags}
                onChange={(e) => setNewNote(prev => ({ ...prev, tags: e.target.value }))}
                placeholder="Enter tags separated by commas"
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setNewNoteDialogOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleAddNote}
                disabled={!newNote.content.trim()}
              >
                Add Note
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Email Composer Dialog */}
      <Dialog open={emailDialogOpen} onOpenChange={setEmailDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Compose Email</DialogTitle>
            <DialogDescription>
              Send a personalized email to {lead.author_name || 'the lead'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="email_to">To</Label>
                <Input
                  id="email_to"
                  value={emailComposer.to}
                  onChange={(e) => setEmailComposer(prev => ({ ...prev, to: e.target.value }))}
                  placeholder="Recipient email address"
                />
              </div>
              
              <div>
                <Label htmlFor="email_template">Template</Label>
                <Select
                  value={emailComposer.template}
                  onValueChange={applyTemplate}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Choose template" />
                  </SelectTrigger>
                  <SelectContent>
                    {communicationTemplates.map(template => (
                      <SelectItem key={template.id} value={template.id}>
                        {template.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label htmlFor="email_subject">Subject</Label>
              <Input
                id="email_subject"
                value={emailComposer.subject}
                onChange={(e) => setEmailComposer(prev => ({ ...prev, subject: e.target.value }))}
                placeholder="Email subject"
              />
            </div>

            <div>
              <Label htmlFor="email_content">Message</Label>
              <Textarea
                id="email_content"
                value={emailComposer.content}
                onChange={(e) => setEmailComposer(prev => ({ ...prev, content: e.target.value }))}
                placeholder="Email content"
                className="min-h-[300px]"
              />
            </div>

            <div className="flex justify-between">
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Paperclip className="mr-2 h-4 w-4" />
                  Attach File
                </Button>
              </div>
              
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setEmailDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  onClick={handleSendEmail}
                  disabled={!emailComposer.to || !emailComposer.subject || !emailComposer.content}
                >
                  <Send className="mr-2 h-4 w-4" />
                  Send Email
                </Button>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}