"use client"

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'
import {
  Lightbulb,
  X,
  Info,
  AlertTriangle,
  HelpCircle,
  Zap,
  ArrowRight
} from 'lucide-react'

interface TooltipConfig {
  content: string
  title?: string
  type?: 'info' | 'help' | 'warning' | 'tip' | 'feature'
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'auto'
  trigger?: 'hover' | 'click' | 'focus' | 'manual'
  delay?: number
  showOnce?: boolean
  persistent?: boolean
  maxWidth?: number
  learnMoreUrl?: string
  priority?: 'low' | 'medium' | 'high'
}

interface TooltipState {
  id: string
  config: TooltipConfig
  targetElement: HTMLElement
  position: { x: number, y: number }
  isVisible: boolean
}

interface TooltipContextType {
  showTooltip: (id: string, targetElement: HTMLElement, config: TooltipConfig) => void
  hideTooltip: (id: string) => void
  hideAllTooltips: () => void
  isTooltipVisible: (id: string) => boolean
  setGlobalEnabled: (enabled: boolean) => void
  isGlobalEnabled: boolean
}

const TooltipContext = createContext<TooltipContextType | undefined>(undefined)

export function useTooltip() {
  const context = useContext(TooltipContext)
  if (!context) {
    throw new Error('useTooltip must be used within a TooltipProvider')
  }
  return context
}

interface TooltipProviderProps {
  children: ReactNode
  globalDelay?: number
  maxConcurrentTooltips?: number
}

export function TooltipProvider({ 
  children, 
  globalDelay = 500,
  maxConcurrentTooltips = 3
}: TooltipProviderProps) {
  const [tooltips, setTooltips] = useState<Map<string, TooltipState>>(new Map())
  const [isGlobalEnabled, setIsGlobalEnabled] = useState(true)
  const [seenTooltips, setSeenTooltips] = useState<Set<string>>(new Set())

  // Load seen tooltips from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('techlead-seen-tooltips')
    if (saved) {
      setSeenTooltips(new Set(JSON.parse(saved)))
    }

    const enabled = localStorage.getItem('techlead-tooltips-enabled')
    if (enabled !== null) {
      setIsGlobalEnabled(JSON.parse(enabled))
    }
  }, [])

  // Save seen tooltips to localStorage
  const markTooltipSeen = (id: string) => {
    const newSeen = new Set(seenTooltips)
    newSeen.add(id)
    setSeenTooltips(newSeen)
    localStorage.setItem('techlead-seen-tooltips', JSON.stringify([...newSeen]))
  }

  const calculatePosition = (targetElement: HTMLElement, placement: string = 'auto') => {
    const rect = targetElement.getBoundingClientRect()
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    
    let x = 0, y = 0
    let finalPlacement = placement

    if (placement === 'auto') {
      // Auto-calculate best placement
      const spaceTop = rect.top
      const spaceBottom = viewportHeight - rect.bottom
      const spaceLeft = rect.left
      const spaceRight = viewportWidth - rect.right

      if (spaceBottom >= 200) finalPlacement = 'bottom'
      else if (spaceTop >= 200) finalPlacement = 'top'
      else if (spaceRight >= 300) finalPlacement = 'right'
      else if (spaceLeft >= 300) finalPlacement = 'left'
      else finalPlacement = 'bottom'
    } else {
      finalPlacement = placement
    }

    switch (finalPlacement) {
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

    return { x, y, placement: finalPlacement }
  }

  const showTooltip = (id: string, targetElement: HTMLElement, config: TooltipConfig) => {
    if (!isGlobalEnabled) return
    if (config.showOnce && seenTooltips.has(id)) return
    if (tooltips.size >= maxConcurrentTooltips) return

    const position = calculatePosition(targetElement, config.placement)
    
    const tooltipState: TooltipState = {
      id,
      config,
      targetElement,
      position,
      isVisible: true
    }

    setTooltips(prev => new Map(prev).set(id, tooltipState))
    markTooltipSeen(id)
  }

  const hideTooltip = (id: string) => {
    setTooltips(prev => {
      const newMap = new Map(prev)
      newMap.delete(id)
      return newMap
    })
  }

  const hideAllTooltips = () => {
    setTooltips(new Map())
  }

  const isTooltipVisible = (id: string) => {
    return tooltips.has(id)
  }

  const setGlobalEnabled = (enabled: boolean) => {
    setIsGlobalEnabled(enabled)
    localStorage.setItem('techlead-tooltips-enabled', JSON.stringify(enabled))
    if (!enabled) {
      hideAllTooltips()
    }
  }

  const contextValue: TooltipContextType = {
    showTooltip,
    hideTooltip,
    hideAllTooltips,
    isTooltipVisible,
    setGlobalEnabled,
    isGlobalEnabled
  }

  return (
    <TooltipContext.Provider value={contextValue}>
      {children}
      <TooltipRenderer tooltips={Array.from(tooltips.values())} onHide={hideTooltip} />
    </TooltipContext.Provider>
  )
}

interface TooltipRendererProps {
  tooltips: TooltipState[]
  onHide: (id: string) => void
}

function TooltipRenderer({ tooltips, onHide }: TooltipRendererProps) {
  if (tooltips.length === 0) return null

  return createPortal(
    <div className="fixed inset-0 z-50 pointer-events-none">
      {tooltips.map((tooltip) => (
        <TooltipContent
          key={tooltip.id}
          tooltip={tooltip}
          onClose={() => onHide(tooltip.id)}
        />
      ))}
    </div>,
    document.body
  )
}

interface TooltipContentProps {
  tooltip: TooltipState
  onClose: () => void
}

function TooltipContent({ tooltip, onClose }: TooltipContentProps) {
  const { config, position } = tooltip
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    // Animate in
    const timer = setTimeout(() => setIsVisible(true), 50)
    return () => clearTimeout(timer)
  }, [])

  const typeConfig = {
    info: { icon: Info, bgColor: 'bg-blue-50', borderColor: 'border-blue-200', textColor: 'text-blue-800' },
    help: { icon: HelpCircle, bgColor: 'bg-gray-50', borderColor: 'border-gray-200', textColor: 'text-gray-800' },
    warning: { icon: AlertTriangle, bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200', textColor: 'text-yellow-800' },
    tip: { icon: Lightbulb, bgColor: 'bg-green-50', borderColor: 'border-green-200', textColor: 'text-green-800' },
    feature: { icon: Zap, bgColor: 'bg-purple-50', borderColor: 'border-purple-200', textColor: 'text-purple-800' }
  }

  const type = config.type || 'info'
  const { icon: Icon, bgColor, borderColor, textColor } = typeConfig[type]
  const placement = (position as any).placement || 'bottom'

  return (
    <div
      className={cn(
        "absolute pointer-events-auto transform transition-all duration-200 z-50",
        isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-95',
        placement === 'top' && 'translate-x-[-50%] translate-y-[-100%]',
        placement === 'bottom' && 'translate-x-[-50%]',
        placement === 'left' && 'translate-x-[-100%] translate-y-[-50%]',
        placement === 'right' && 'translate-y-[-50%]'
      )}
      style={{
        left: position.x,
        top: position.y,
        maxWidth: config.maxWidth || 320
      }}
    >
      {/* Arrow */}
      <div
        className={cn(
          "absolute w-3 h-3 border transform rotate-45",
          bgColor,
          borderColor,
          placement === 'top' && 'bottom-[-6px] left-1/2 -translate-x-1/2 border-r border-b border-l-0 border-t-0',
          placement === 'bottom' && 'top-[-6px] left-1/2 -translate-x-1/2 border-l border-t border-r-0 border-b-0',
          placement === 'left' && 'right-[-6px] top-1/2 -translate-y-1/2 border-t border-r border-b-0 border-l-0',
          placement === 'right' && 'left-[-6px] top-1/2 -translate-y-1/2 border-b border-l border-t-0 border-r-0'
        )}
      />

      {/* Content */}
      <div className={cn(
        "relative rounded-lg border shadow-lg p-4",
        bgColor,
        borderColor
      )}>
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center",
              type === 'info' && 'bg-blue-100',
              type === 'help' && 'bg-gray-100',
              type === 'warning' && 'bg-yellow-100',
              type === 'tip' && 'bg-green-100',
              type === 'feature' && 'bg-purple-100'
            )}>
              <Icon className={cn(
                "w-4 h-4",
                type === 'info' && 'text-blue-600',
                type === 'help' && 'text-gray-600',
                type === 'warning' && 'text-yellow-600',
                type === 'tip' && 'text-green-600',
                type === 'feature' && 'text-purple-600'
              )} />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            {config.title && (
              <h4 className={cn("font-medium text-sm mb-1", textColor)}>
                {config.title}
              </h4>
            )}
            <p className={cn("text-sm leading-relaxed", textColor)}>
              {config.content}
            </p>

            {config.learnMoreUrl && (
              <div className="mt-3">
                <button
                  onClick={() => window.open(config.learnMoreUrl, '_blank')}
                  className={cn(
                    "inline-flex items-center space-x-1 text-xs font-medium hover:underline",
                    type === 'info' && 'text-blue-600',
                    type === 'help' && 'text-gray-600',
                    type === 'warning' && 'text-yellow-600',
                    type === 'tip' && 'text-green-600',
                    type === 'feature' && 'text-purple-600'
                  )}
                >
                  <span>Learn more</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>

          {!config.persistent && (
            <button
              onClick={onClose}
              className={cn(
                "flex-shrink-0 p-1 rounded-full hover:bg-black/5 transition-colors",
                textColor
              )}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}