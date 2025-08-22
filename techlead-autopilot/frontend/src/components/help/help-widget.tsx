"use client"

import React, { useState } from 'react'
import { createPortal } from 'react-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  HelpCircle,
  X,
  Search,
  Book,
  MessageCircle,
  FileText,
  ExternalLink,
  ChevronRight,
  Lightbulb,
  Zap,
  Users,
  BarChart3,
  Settings
} from 'lucide-react'

interface QuickHelp {
  id: string
  title: string
  description: string
  category: 'getting-started' | 'content' | 'leads' | 'analytics' | 'settings'
  action: () => void
  icon: React.ComponentType<{ className?: string }>
}

interface HelpWidgetProps {
  className?: string
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'
  size?: 'small' | 'medium' | 'large'
}

const quickHelpItems: QuickHelp[] = [
  {
    id: 'getting-started',
    title: 'Getting Started Guide',
    description: 'Learn the basics in 5 minutes',
    category: 'getting-started',
    icon: Lightbulb,
    action: () => window.open('/help?article=quick-start-guide', '_blank')
  },
  {
    id: 'generate-content',
    title: 'Generate Your First Content',
    description: 'Create engaging technical content',
    category: 'content',
    icon: FileText,
    action: () => window.location.href = '/dashboard/content/generate'
  },
  {
    id: 'understand-leads',
    title: 'Understanding Lead Scoring',
    description: 'Learn how we identify opportunities',
    category: 'leads',
    icon: Users,
    action: () => window.open('/help?article=lead-scoring-explained', '_blank')
  },
  {
    id: 'analytics-guide',
    title: 'Analytics Dashboard',
    description: 'Track your performance',
    category: 'analytics',
    icon: BarChart3,
    action: () => window.open('/help?article=analytics-dashboard-guide', '_blank')
  },
  {
    id: 'keyboard-shortcuts',
    title: 'Keyboard Shortcuts',
    description: 'Speed up your workflow',
    category: 'settings',
    icon: Zap,
    action: () => window.open('/help?article=keyboard-shortcuts', '_blank')
  }
]

const contactOptions = [
  {
    id: 'help-center',
    title: 'Browse Help Center',
    description: 'Search our comprehensive documentation',
    icon: Book,
    action: () => window.open('/help', '_blank')
  },
  {
    id: 'contact-support',
    title: 'Contact Support',
    description: 'Get personalized help from our team',
    icon: MessageCircle,
    action: () => window.open('mailto:support@techleadautopilot.com', '_blank')
  }
]

const positionClasses = {
  'bottom-right': 'bottom-6 right-6',
  'bottom-left': 'bottom-6 left-6',
  'top-right': 'top-6 right-6',
  'top-left': 'top-6 left-6'
}

export function HelpWidget({ 
  className, 
  position = 'bottom-right',
  size = 'medium'
}: HelpWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'quick-help' | 'search' | 'contact'>('quick-help')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredQuickHelp = searchQuery
    ? quickHelpItems.filter(item =>
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : quickHelpItems

  const widgetSize = {
    small: 'w-80',
    medium: 'w-96',
    large: 'w-[28rem]'
  }[size]

  const handleQuickAction = (action: () => void) => {
    action()
    setIsOpen(false)
  }

  if (!isOpen) {
    return (
      <div className={cn("fixed z-50", positionClasses[position], className)}>
        <Button
          onClick={() => setIsOpen(true)}
          className="rounded-full w-14 h-14 shadow-lg hover:shadow-xl transition-all duration-200 bg-blue-600 hover:bg-blue-700"
          aria-label="Open help"
        >
          <HelpCircle className="w-6 h-6" />
        </Button>
      </div>
    )
  }

  const widget = (
    <div className={cn(
      "fixed z-50",
      positionClasses[position],
      widgetSize,
      className
    )}>
      <Card className="shadow-2xl border-0 bg-white">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2 text-lg">
              <HelpCircle className="w-5 h-5 text-blue-600" />
              <span>Need Help?</span>
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsOpen(false)}
              className="h-8 w-8 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
          
          {/* Tab Navigation */}
          <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mt-3">
            <button
              onClick={() => setActiveTab('quick-help')}
              className={cn(
                "flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                activeTab === 'quick-help'
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              )}
            >
              Quick Help
            </button>
            <button
              onClick={() => setActiveTab('search')}
              className={cn(
                "flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                activeTab === 'search'
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              )}
            >
              Search
            </button>
            <button
              onClick={() => setActiveTab('contact')}
              className={cn(
                "flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                activeTab === 'contact'
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              )}
            >
              Contact
            </button>
          </div>
        </CardHeader>

        <CardContent className="space-y-3 max-h-96 overflow-y-auto">
          {activeTab === 'quick-help' && (
            <div className="space-y-2">
              {filteredQuickHelp.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.id}
                    onClick={() => handleQuickAction(item.action)}
                    className="w-full p-3 text-left rounded-lg border border-gray-200 hover:border-blue-200 hover:bg-blue-50 transition-all duration-150"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Icon className="w-4 h-4 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-gray-900 mb-1">
                          {item.title}
                        </div>
                        <div className="text-xs text-gray-600">
                          {item.description}
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    </div>
                  </button>
                )
              })}
            </div>
          )}

          {activeTab === 'search' && (
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Search help articles..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 text-sm"
                />
              </div>
              
              {searchQuery && (
                <div className="space-y-2">
                  {filteredQuickHelp.length > 0 ? (
                    filteredQuickHelp.map((item) => {
                      const Icon = item.icon
                      return (
                        <button
                          key={item.id}
                          onClick={() => handleQuickAction(item.action)}
                          className="w-full p-2 text-left rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex items-center space-x-2">
                            <Icon className="w-4 h-4 text-blue-600" />
                            <div>
                              <div className="font-medium text-sm">{item.title}</div>
                              <div className="text-xs text-gray-600">{item.description}</div>
                            </div>
                          </div>
                        </button>
                      )
                    })
                  ) : (
                    <div className="text-center py-4">
                      <p className="text-sm text-gray-500 mb-3">No quick help found</p>
                      <Button
                        size="sm"
                        onClick={() => window.open(`/help?search=${searchQuery}`, '_blank')}
                        className="text-xs"
                      >
                        Search All Articles
                      </Button>
                    </div>
                  )}
                </div>
              )}
              
              {!searchQuery && (
                <div className="text-center py-6">
                  <Search className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-sm text-gray-500 mb-3">
                    Search our help articles
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => window.open('/help', '_blank')}
                  >
                    Browse All Articles
                  </Button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'contact' && (
            <div className="space-y-2">
              {contactOptions.map((option) => {
                const Icon = option.icon
                return (
                  <button
                    key={option.id}
                    onClick={() => handleQuickAction(option.action)}
                    className="w-full p-3 text-left rounded-lg border border-gray-200 hover:border-blue-200 hover:bg-blue-50 transition-all duration-150"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Icon className="w-4 h-4 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-gray-900 mb-1">
                          {option.title}
                        </div>
                        <div className="text-xs text-gray-600">
                          {option.description}
                        </div>
                      </div>
                      <ExternalLink className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    </div>
                  </button>
                )
              })}
              
              <div className="pt-3 mt-3 border-t border-gray-200">
                <div className="text-xs text-gray-500 text-center">
                  Response time: Usually within 2-4 hours
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )

  return createPortal(widget, document.body)
}

// Hook for managing help widget
export function useHelpWidget() {
  const [isVisible, setIsVisible] = useState(true)

  const toggleVisibility = (visible?: boolean) => {
    setIsVisible(visible !== undefined ? visible : !isVisible)
  }

  const showHelp = (topic?: string) => {
    if (topic) {
      window.open(`/help?search=${topic}`, '_blank')
    } else {
      window.open('/help', '_blank')
    }
  }

  return {
    isVisible,
    toggleVisibility,
    showHelp
  }
}