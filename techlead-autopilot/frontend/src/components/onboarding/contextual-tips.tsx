"use client"

import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Lightbulb,
  X,
  ChevronRight,
  Zap,
  Target,
  FileText,
  Users,
  BarChart3,
  Settings,
  Clock,
  Heart,
  TrendingUp,
  MessageSquare,
  Calendar,
  CheckCircle,
  ArrowRight
} from 'lucide-react'

interface ContextualTip {
  id: string
  title: string
  content: string
  icon?: React.ComponentType<{ className?: string }>
  trigger: {
    selector: string
    event?: 'hover' | 'click' | 'focus' | 'auto'
    delay?: number
  }
  placement?: 'top' | 'bottom' | 'left' | 'right'
  category: 'navigation' | 'feature' | 'workflow' | 'optimization'
  priority: 'high' | 'medium' | 'low'
  showOnce?: boolean
  conditions?: {
    path?: string
    pathPattern?: string
    userAction?: string
    timeOnPage?: number
  }
  cta?: {
    text: string
    action: () => void
  }
}

interface ContextualTipsProps {
  isEnabled?: boolean
  showDebugInfo?: boolean
}

const contextualTips: ContextualTip[] = [
  // Navigation Tips
  {
    id: 'sidebar-collapse',
    title: 'Toggle Sidebar',
    content: 'Press ⌘B (Ctrl+B on Windows) to quickly collapse or expand the sidebar for more workspace.',
    icon: Target,
    trigger: { selector: '[data-tour="sidebar"]', event: 'hover', delay: 2000 },
    placement: 'right',
    category: 'navigation',
    priority: 'medium',
    showOnce: true
  },
  {
    id: 'universal-search',
    title: 'Quick Search Everything',
    content: 'Use ⌘K to instantly search content, leads, analytics, or navigate anywhere in the platform.',
    icon: Zap,
    trigger: { selector: '[data-tour="search-button"]', event: 'hover', delay: 1500 },
    placement: 'bottom',
    category: 'navigation',
    priority: 'high',
    showOnce: true
  },
  
  // Content Management Tips
  {
    id: 'content-generation-tip',
    title: 'Content Generation Best Practice',
    content: 'Include specific details about your experience and industry for more personalized, engaging content.',
    icon: FileText,
    trigger: { selector: 'input[placeholder*="topic"]', event: 'focus', delay: 3000 },
    placement: 'top',
    category: 'feature',
    priority: 'high',
    conditions: { path: '/dashboard/content/generate' }
  },
  {
    id: 'content-approval-workflow',
    title: 'Smart Approval Process',
    content: 'Review generated content in the preview pane. Edit directly or regenerate with different parameters.',
    icon: CheckCircle,
    trigger: { selector: '[data-testid="content-preview"]', event: 'auto', delay: 2000 },
    placement: 'left',
    category: 'workflow',
    priority: 'medium',
    conditions: { pathPattern: '/dashboard/content' }
  },
  {
    id: 'content-scheduling',
    title: 'Optimal Posting Times',
    content: 'Tuesday and Thursday at 6:30 AM show the highest engagement rates for technical leadership content.',
    icon: Calendar,
    trigger: { selector: 'button[data-action="schedule"]', event: 'hover', delay: 1000 },
    placement: 'top',
    category: 'optimization',
    priority: 'high',
    conditions: { pathPattern: '/dashboard/content' }
  },
  
  // Lead Management Tips
  {
    id: 'lead-scoring-insight',
    title: 'Lead Scoring Guide',
    content: 'Scores 8+ indicate high consultation potential. Focus on leads mentioning "challenges" or "help needed".',
    icon: Users,
    trigger: { selector: '[data-component="lead-score"]', event: 'hover', delay: 1500 },
    placement: 'top',
    category: 'feature',
    priority: 'high',
    conditions: { pathPattern: '/dashboard/leads' }
  },
  {
    id: 'lead-follow-up',
    title: 'Follow-up Strategy',
    content: 'Respond within 2 hours for hot leads. Personalize your message referencing their specific comment or question.',
    icon: MessageSquare,
    trigger: { selector: '[data-priority="high"]', event: 'click', delay: 500 },
    placement: 'right',
    category: 'workflow',
    priority: 'high',
    conditions: { pathPattern: '/dashboard/leads' }
  },
  {
    id: 'pipeline-value-insight',
    title: 'Pipeline Value Tracking',
    content: 'This represents potential consultation value. Track conversions to refine your lead scoring accuracy.',
    icon: TrendingUp,
    trigger: { selector: '[data-metric="pipeline-value"]', event: 'hover', delay: 2000 },
    placement: 'top',
    category: 'feature',
    priority: 'medium',
    conditions: { pathPattern: '/dashboard/leads' }
  },
  
  // Analytics Tips
  {
    id: 'engagement-analytics',
    title: 'Content Performance Insights',
    content: 'High engagement posts often include personal stories, specific metrics, or controversial but professional opinions.',
    icon: BarChart3,
    trigger: { selector: '[data-chart="engagement"]', event: 'hover', delay: 2000 },
    placement: 'top',
    category: 'optimization',
    priority: 'medium',
    conditions: { pathPattern: '/dashboard/content/analytics' }
  },
  {
    id: 'attribution-analysis',
    title: 'Content-to-Lead Attribution',
    content: 'Track which content types generate the most qualified leads to optimize your content strategy.',
    icon: Target,
    trigger: { selector: '[data-chart="attribution"]', event: 'auto', delay: 3000 },
    placement: 'left',
    category: 'optimization',
    priority: 'high',
    conditions: { pathPattern: '/dashboard/content/analytics' }
  },
  
  // Dashboard Tips
  {
    id: 'dashboard-overview',
    title: 'Your Command Center',
    content: 'This overview shows your weekly performance. Green trends indicate growing influence and lead generation.',
    icon: LayoutDashboard,
    trigger: { selector: '[data-component="stats-overview"]', event: 'auto', delay: 5000 },
    placement: 'top',
    category: 'feature',
    priority: 'medium',
    conditions: { path: '/dashboard' }
  },
  {
    id: 'quick-actions',
    title: 'Quick Actions Hub',
    content: 'Use these shortcuts for your most common tasks. They adapt based on your usage patterns.',
    icon: Zap,
    trigger: { selector: '[data-component="quick-actions"]', event: 'hover', delay: 1500 },
    placement: 'bottom',
    category: 'navigation',
    priority: 'low',
    conditions: { path: '/dashboard' }
  },
  
  // Settings & Optimization Tips
  {
    id: 'profile-optimization',
    title: 'Profile Optimization Impact',
    content: 'Complete profiles generate 40% more personalized content and better lead detection accuracy.',
    icon: Settings,
    trigger: { selector: 'form[data-form="profile"]', event: 'auto', delay: 2000 },
    placement: 'right',
    category: 'optimization',
    priority: 'high',
    conditions: { pathPattern: '/dashboard/settings' }
  },
  {
    id: 'integration-benefits',
    title: 'LinkedIn Integration Benefits',
    content: 'Connected accounts enable automatic posting, engagement tracking, and lead detection from your content.',
    icon: Heart,
    trigger: { selector: '[data-integration="linkedin"]', event: 'hover', delay: 1000 },
    placement: 'top',
    category: 'feature',
    priority: 'high',
    conditions: { pathPattern: '/dashboard/settings' }
  }
]

export function ContextualTips({ isEnabled = true, showDebugInfo = false }: ContextualTipsProps) {
  const [activeTip, setActiveTip] = useState<ContextualTip | null>(null)
  const [dismissedTips, setDismissedTips] = useState<Set<string>>(new Set())
  const [tipPosition, setTipPosition] = useState({ x: 0, y: 0 })
  const [hoveredElement, setHoveredElement] = useState<HTMLElement | null>(null)
  const [timeOnPage, setTimeOnPage] = useState(0)
  
  const pathname = usePathname()
  const tipRef = useRef<HTMLDivElement>(null)
  const hoverTimeoutRef = useRef<NodeJS.Timeout>()
  const autoTipTimeoutRef = useRef<NodeJS.Timeout>()

  // Load dismissed tips from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('techlead-dismissed-tips')
    if (saved) {
      setDismissedTips(new Set(JSON.parse(saved)))
    }
  }, [])

  // Track time on page
  useEffect(() => {
    const startTime = Date.now()
    const interval = setInterval(() => {
      setTimeOnPage(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [pathname])

  // Filter tips based on current conditions
  const getRelevantTips = () => {
    return contextualTips.filter(tip => {
      // Skip dismissed tips
      if (tip.showOnce && dismissedTips.has(tip.id)) return false
      
      // Check path conditions
      if (tip.conditions?.path && tip.conditions.path !== pathname) return false
      if (tip.conditions?.pathPattern && !pathname.includes(tip.conditions.pathPattern)) return false
      if (tip.conditions?.timeOnPage && timeOnPage < tip.conditions.timeOnPage) return false
      
      return true
    })
  }

  // Set up event listeners for triggers
  useEffect(() => {
    if (!isEnabled) return

    const relevantTips = getRelevantTips()
    const listeners: Array<{ element: HTMLElement, event: string, handler: () => void }> = []

    relevantTips.forEach(tip => {
      const elements = document.querySelectorAll(tip.trigger.selector)
      
      elements.forEach(element => {
        const htmlElement = element as HTMLElement
        
        const showTip = (e?: Event) => {
          if (activeTip && activeTip.id === tip.id) return
          
          const rect = htmlElement.getBoundingClientRect()
          const placement = tip.placement || 'top'
          
          let x = 0, y = 0
          
          switch (placement) {
            case 'top':
              x = rect.left + rect.width / 2
              y = rect.top - 10
              break
            case 'bottom':
              x = rect.left + rect.width / 2
              y = rect.bottom + 10
              break
            case 'left':
              x = rect.left - 10
              y = rect.top + rect.height / 2
              break
            case 'right':
              x = rect.right + 10
              y = rect.top + rect.height / 2
              break
          }
          
          setTipPosition({ x, y })
          setActiveTip(tip)
          setHoveredElement(htmlElement)
        }

        const hideTip = () => {
          if (hoverTimeoutRef.current) {
            clearTimeout(hoverTimeoutRef.current)
          }
          setActiveTip(null)
          setHoveredElement(null)
        }

        switch (tip.trigger.event) {
          case 'hover':
            const hoverHandler = () => {
              hoverTimeoutRef.current = setTimeout(showTip, tip.trigger.delay || 1000)
            }
            const leaveHandler = () => {
              hideTip()
            }
            
            htmlElement.addEventListener('mouseenter', hoverHandler)
            htmlElement.addEventListener('mouseleave', leaveHandler)
            
            listeners.push(
              { element: htmlElement, event: 'mouseenter', handler: hoverHandler },
              { element: htmlElement, event: 'mouseleave', handler: leaveHandler }
            )
            break
            
          case 'click':
            const clickHandler = () => {
              setTimeout(showTip, tip.trigger.delay || 500)
            }
            htmlElement.addEventListener('click', clickHandler)
            listeners.push({ element: htmlElement, event: 'click', handler: clickHandler })
            break
            
          case 'focus':
            const focusHandler = () => {
              setTimeout(showTip, tip.trigger.delay || 1000)
            }
            htmlElement.addEventListener('focus', focusHandler)
            listeners.push({ element: htmlElement, event: 'focus', handler: focusHandler })
            break
            
          case 'auto':
            autoTipTimeoutRef.current = setTimeout(showTip, tip.trigger.delay || 2000)
            break
        }
      })
    })

    return () => {
      listeners.forEach(({ element, event, handler }) => {
        element.removeEventListener(event, handler)
      })
      
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current)
      if (autoTipTimeoutRef.current) clearTimeout(autoTipTimeoutRef.current)
    }
  }, [pathname, isEnabled, timeOnPage, dismissedTips, activeTip])

  // Handle tip dismissal
  const dismissTip = (tipId: string, permanent = false) => {
    setActiveTip(null)
    setHoveredElement(null)
    
    if (permanent) {
      const newDismissed = new Set(dismissedTips)
      newDismissed.add(tipId)
      setDismissedTips(newDismissed)
      localStorage.setItem('techlead-dismissed-tips', JSON.stringify([...newDismissed]))
    }
  }

  // Handle tip action
  const handleTipAction = (tip: ContextualTip) => {
    if (tip.cta?.action) {
      tip.cta.action()
    }
    dismissTip(tip.id, true)
  }

  if (!isEnabled || !activeTip) return null

  const Icon = activeTip.icon || Lightbulb

  return createPortal(
    <div className="fixed inset-0 z-[9998] pointer-events-none">
      {/* Highlight overlay for hovered element */}
      {hoveredElement && (
        <div
          className="absolute border-2 border-blue-400/50 bg-blue-400/10 rounded-lg pointer-events-none transition-all duration-200"
          style={{
            left: hoveredElement.getBoundingClientRect().left - 2,
            top: hoveredElement.getBoundingClientRect().top - 2,
            width: hoveredElement.getBoundingClientRect().width + 4,
            height: hoveredElement.getBoundingClientRect().height + 4
          }}
        />
      )}

      {/* Tip Card */}
      <Card
        ref={tipRef}
        className={cn(
          "absolute max-w-sm shadow-lg border-blue-200 bg-gradient-to-br from-blue-50 to-white pointer-events-auto transform transition-all duration-300",
          activeTip.placement === 'top' && 'translate-x-[-50%] translate-y-[-100%]',
          activeTip.placement === 'bottom' && 'translate-x-[-50%]',
          activeTip.placement === 'left' && 'translate-x-[-100%] translate-y-[-50%]',
          activeTip.placement === 'right' && 'translate-y-[-50%]'
        )}
        style={{
          left: tipPosition.x,
          top: tipPosition.y,
          zIndex: 9999
        }}
      >
        <CardContent className="p-4">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                <Icon className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <h4 className="font-medium text-blue-900 text-sm">{activeTip.title}</h4>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                    {activeTip.category}
                  </span>
                  {activeTip.priority === 'high' && (
                    <span className="text-xs text-orange-600 bg-orange-100 px-2 py-0.5 rounded-full">
                      Priority
                    </span>
                  )}
                </div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => dismissTip(activeTip.id)}
              className="p-1 h-6 w-6 text-gray-400 hover:text-gray-600"
            >
              <X className="w-3 h-3" />
            </Button>
          </div>

          {/* Content */}
          <p className="text-sm text-blue-800 leading-relaxed mb-4">
            {activeTip.content}
          </p>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {activeTip.cta && (
                <Button
                  size="sm"
                  onClick={() => handleTipAction(activeTip)}
                  className="text-xs"
                >
                  {activeTip.cta.text}
                  <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              )}
            </div>
            
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => dismissTip(activeTip.id, false)}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                Later
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => dismissTip(activeTip.id, true)}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                Got it
              </Button>
            </div>
          </div>

          {/* Debug info */}
          {showDebugInfo && (
            <div className="mt-3 pt-3 border-t border-blue-200 text-xs text-gray-500">
              <div>ID: {activeTip.id}</div>
              <div>Trigger: {activeTip.trigger.selector}</div>
              <div>Time on page: {timeOnPage}s</div>
            </div>
          )}
        </CardContent>

        {/* Arrow */}
        <div
          className={cn(
            "absolute w-3 h-3 bg-gradient-to-br from-blue-50 to-white border-blue-200",
            activeTip.placement === 'top' && 'bottom-[-6px] left-1/2 transform -translate-x-1/2 rotate-45 border-r border-b',
            activeTip.placement === 'bottom' && 'top-[-6px] left-1/2 transform -translate-x-1/2 rotate-45 border-l border-t',
            activeTip.placement === 'left' && 'right-[-6px] top-1/2 transform -translate-y-1/2 rotate-45 border-t border-r',
            activeTip.placement === 'right' && 'left-[-6px] top-1/2 transform -translate-y-1/2 rotate-45 border-b border-l'
          )}
        />
      </Card>
    </div>,
    document.body
  )
}

// Hook for managing contextual tips
export function useContextualTips() {
  const [isEnabled, setIsEnabled] = useState(true)
  const [showDebugInfo, setShowDebugInfo] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('techlead-contextual-tips-enabled')
    if (saved !== null) {
      setIsEnabled(JSON.parse(saved))
    }
  }, [])

  const toggleTips = (enabled?: boolean) => {
    const newState = enabled !== undefined ? enabled : !isEnabled
    setIsEnabled(newState)
    localStorage.setItem('techlead-contextual-tips-enabled', JSON.stringify(newState))
  }

  const clearDismissedTips = () => {
    localStorage.removeItem('techlead-dismissed-tips')
    window.location.reload() // Simple way to reset tip state
  }

  const toggleDebugMode = () => {
    setShowDebugInfo(!showDebugInfo)
  }

  return {
    isEnabled,
    showDebugInfo,
    toggleTips,
    toggleDebugMode,
    clearDismissedTips
  }
}