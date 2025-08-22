"use client"

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  CheckCircle2,
  Circle,
  ArrowRight,
  Sparkles,
  FileText,
  Users,
  Settings,
  BarChart3,
  Lightbulb,
  Trophy,
  Clock,
  Target
} from 'lucide-react'

interface ChecklistItem {
  id: string
  title: string
  description: string
  href?: string
  action?: () => void
  icon: React.ComponentType<{ className?: string }>
  estimatedTime: string
  points: number
  category: 'setup' | 'content' | 'leads' | 'optimization'
  isCompleted?: boolean
  isOptional?: boolean
  prerequisite?: string[]
}

interface WelcomeChecklistProps {
  className?: string
  onItemComplete?: (itemId: string) => void
  onAllComplete?: () => void
}

const checklistItems: ChecklistItem[] = [
  // Setup Phase
  {
    id: 'complete-profile',
    title: 'Complete Your Profile',
    description: 'Add your job title, company, and LinkedIn URL to personalize your content generation.',
    href: '/dashboard/settings/profile',
    icon: Settings,
    estimatedTime: '2 min',
    points: 10,
    category: 'setup'
  },
  {
    id: 'take-tour',
    title: 'Take the Product Tour',
    description: 'Get familiar with the platform features and learn keyboard shortcuts.',
    icon: Lightbulb,
    estimatedTime: '3 min',
    points: 5,
    category: 'setup'
  },
  
  // Content Phase
  {
    id: 'generate-first-content',
    title: 'Generate Your First Content',
    description: 'Create a LinkedIn post about your technical leadership experience.',
    href: '/dashboard/content/generate',
    icon: FileText,
    estimatedTime: '5 min',
    points: 25,
    category: 'content',
    prerequisite: ['complete-profile']
  },
  {
    id: 'approve-content',
    title: 'Review and Approve Content',
    description: 'Edit your generated content and approve it for posting.',
    href: '/dashboard/content',
    icon: CheckCircle2,
    estimatedTime: '3 min',
    points: 15,
    category: 'content',
    prerequisite: ['generate-first-content']
  },
  {
    id: 'schedule-content',
    title: 'Schedule Your First Post',
    description: 'Choose optimal timing for your content to maximize engagement.',
    href: '/dashboard/content',
    icon: Clock,
    estimatedTime: '2 min',
    points: 20,
    category: 'content',
    prerequisite: ['approve-content']
  },
  
  // Lead Generation Phase
  {
    id: 'understand-leads',
    title: 'Explore Lead Detection',
    description: 'Learn how the platform identifies consultation opportunities from your content.',
    href: '/dashboard/leads',
    icon: Users,
    estimatedTime: '3 min',
    points: 15,
    category: 'leads',
    isOptional: true
  },
  {
    id: 'setup-notifications',
    title: 'Enable Lead Notifications',
    description: 'Get instant alerts when high-priority leads are detected.',
    href: '/dashboard/settings/notifications',
    icon: Target,
    estimatedTime: '2 min',
    points: 10,
    category: 'leads',
    isOptional: true
  },
  
  // Optimization Phase
  {
    id: 'view-analytics',
    title: 'Check Your Analytics',
    description: 'Understand your content performance and lead generation metrics.',
    href: '/dashboard/content/analytics',
    icon: BarChart3,
    estimatedTime: '4 min',
    points: 20,
    category: 'optimization',
    prerequisite: ['schedule-content'],
    isOptional: true
  },
  {
    id: 'generate-multiple-content',
    title: 'Generate 3 More Posts',
    description: 'Build your content library with diverse technical leadership topics.',
    href: '/dashboard/content/generate',
    icon: Sparkles,
    estimatedTime: '15 min',
    points: 50,
    category: 'optimization',
    prerequisite: ['schedule-content'],
    isOptional: true
  }
]

const categoryConfig = {
  setup: { label: 'Account Setup', color: 'bg-blue-500', icon: Settings },
  content: { label: 'Content Creation', color: 'bg-green-500', icon: FileText },
  leads: { label: 'Lead Generation', color: 'bg-purple-500', icon: Users },
  optimization: { label: 'Optimization', color: 'bg-orange-500', icon: BarChart3 }
}

export function WelcomeChecklist({ className, onItemComplete, onAllComplete }: WelcomeChecklistProps) {
  const [completedItems, setCompletedItems] = useState<Set<string>>(new Set())
  const [expandedCategory, setExpandedCategory] = useState<string>('setup')
  const router = useRouter()

  // Load completed items from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('techlead-checklist-completed')
    if (saved) {
      setCompletedItems(new Set(JSON.parse(saved)))
    }
  }, [])

  // Save completed items to localStorage
  useEffect(() => {
    localStorage.setItem('techlead-checklist-completed', JSON.stringify([...completedItems]))
  }, [completedItems])

  // Check prerequisites
  const isItemAvailable = (item: ChecklistItem) => {
    if (!item.prerequisite) return true
    return item.prerequisite.every(prereq => completedItems.has(prereq))
  }

  // Mark item as completed
  const completeItem = (itemId: string) => {
    const newCompleted = new Set(completedItems)
    newCompleted.add(itemId)
    setCompletedItems(newCompleted)
    onItemComplete?.(itemId)

    // Check if all required items are completed
    const requiredItems = checklistItems.filter(item => !item.isOptional)
    const allRequired = requiredItems.every(item => newCompleted.has(item.id))
    
    if (allRequired) {
      onAllComplete?.()
    }
  }

  // Calculate progress
  const totalPoints = checklistItems.reduce((sum, item) => sum + item.points, 0)
  const earnedPoints = checklistItems
    .filter(item => completedItems.has(item.id))
    .reduce((sum, item) => sum + item.points, 0)
  const progressPercentage = (earnedPoints / totalPoints) * 100

  const requiredItemsCompleted = checklistItems
    .filter(item => !item.isOptional)
    .filter(item => completedItems.has(item.id)).length
  const totalRequiredItems = checklistItems.filter(item => !item.isOptional).length

  // Group items by category
  const itemsByCategory = checklistItems.reduce((acc, item) => {
    if (!acc[item.category]) acc[item.category] = []
    acc[item.category].push(item)
    return acc
  }, {} as Record<string, ChecklistItem[]>)

  const handleItemClick = (item: ChecklistItem) => {
    if (item.action) {
      item.action()
    } else if (item.href) {
      router.push(item.href)
    }
    
    // Mark as completed if not already
    if (!completedItems.has(item.id)) {
      completeItem(item.id)
    }
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <Trophy className="w-5 h-5 text-yellow-500" />
              <span>Welcome Checklist</span>
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              Complete these steps to unlock your technical leadership potential
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">{earnedPoints}</div>
            <div className="text-xs text-gray-500">of {totalPoints} points</div>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">
              {requiredItemsCompleted} of {totalRequiredItems} required steps
            </span>
            <span className="text-gray-600">
              {Math.round(progressPercentage)}% complete
            </span>
          </div>
          <Progress value={progressPercentage} className="h-2" />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {Object.entries(itemsByCategory).map(([category, items]) => {
          const categoryInfo = categoryConfig[category as keyof typeof categoryConfig]
          const CategoryIcon = categoryInfo.icon
          const completedInCategory = items.filter(item => completedItems.has(item.id)).length
          const isExpanded = expandedCategory === category
          
          return (
            <div key={category} className="border rounded-lg overflow-hidden">
              {/* Category Header */}
              <button
                onClick={() => setExpandedCategory(isExpanded ? '' : category)}
                className="w-full p-4 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
              >
                <div className="flex items-center space-x-3">
                  <div className={cn("w-8 h-8 rounded-full flex items-center justify-center", categoryInfo.color)}>
                    <CategoryIcon className="w-4 h-4 text-white" />
                  </div>
                  <div className="text-left">
                    <h3 className="font-medium text-gray-900">{categoryInfo.label}</h3>
                    <p className="text-sm text-gray-500">
                      {completedInCategory} of {items.length} completed
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant={completedInCategory === items.length ? 'default' : 'outline'}>
                    {completedInCategory}/{items.length}
                  </Badge>
                  <ArrowRight className={cn(
                    "w-4 h-4 transition-transform",
                    isExpanded ? "rotate-90" : ""
                  )} />
                </div>
              </button>

              {/* Category Items */}
              {isExpanded && (
                <div className="divide-y">
                  {items.map((item) => {
                    const isCompleted = completedItems.has(item.id)
                    const isAvailable = isItemAvailable(item)
                    const Icon = item.icon

                    return (
                      <div
                        key={item.id}
                        className={cn(
                          "p-4 transition-colors",
                          isCompleted ? "bg-green-50" : isAvailable ? "hover:bg-gray-50" : "bg-gray-100"
                        )}
                      >
                        <div className="flex items-start space-x-3">
                          {/* Status Icon */}
                          <div className="flex-shrink-0 mt-1">
                            {isCompleted ? (
                              <CheckCircle2 className="w-5 h-5 text-green-600" />
                            ) : (
                              <Circle className={cn(
                                "w-5 h-5",
                                isAvailable ? "text-gray-400" : "text-gray-300"
                              )} />
                            )}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2 mb-1">
                              <Icon className={cn(
                                "w-4 h-4",
                                isCompleted ? "text-green-600" : isAvailable ? "text-gray-600" : "text-gray-400"
                              )} />
                              <h4 className={cn(
                                "font-medium",
                                isCompleted ? "text-green-900" : isAvailable ? "text-gray-900" : "text-gray-500"
                              )}>
                                {item.title}
                              </h4>
                              {item.isOptional && (
                                <Badge variant="outline" className="text-xs">
                                  Optional
                                </Badge>
                              )}
                            </div>
                            <p className={cn(
                              "text-sm mb-2",
                              isCompleted ? "text-green-700" : isAvailable ? "text-gray-600" : "text-gray-400"
                            )}>
                              {item.description}
                            </p>
                            <div className="flex items-center space-x-4 text-xs">
                              <span className={cn(
                                "flex items-center space-x-1",
                                isCompleted ? "text-green-600" : isAvailable ? "text-gray-500" : "text-gray-400"
                              )}>
                                <Clock className="w-3 h-3" />
                                <span>{item.estimatedTime}</span>
                              </span>
                              <span className={cn(
                                "flex items-center space-x-1",
                                isCompleted ? "text-green-600" : isAvailable ? "text-blue-600" : "text-gray-400"
                              )}>
                                <Sparkles className="w-3 h-3" />
                                <span>{item.points} points</span>
                              </span>
                            </div>
                          </div>

                          {/* Action Button */}
                          {!isCompleted && isAvailable && (
                            <Button
                              size="sm"
                              onClick={() => handleItemClick(item)}
                              className="flex-shrink-0"
                            >
                              Start
                            </Button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}

        {/* Completion Badge */}
        {requiredItemsCompleted === totalRequiredItems && (
          <div className="mt-6 p-4 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <Trophy className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h3 className="font-semibold text-green-900">Congratulations! 🎉</h3>
                <p className="text-sm text-green-700">
                  You've completed the essential setup. Your technical leadership automation is ready to generate business value!
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}