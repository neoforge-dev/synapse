import { useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'

interface TipAction {
  id: string
  action: string
  metadata?: Record<string, any>
}

interface UseContextualTipsProps {
  componentName: string
  trackActions?: boolean
}

// Hook for components to integrate with contextual tips system
export function useContextualTips({ 
  componentName, 
  trackActions = false 
}: UseContextualTipsProps) {
  const pathname = usePathname()
  const actionsRef = useRef<TipAction[]>([])

  // Track user actions for tip personalization
  const trackAction = (action: string, metadata?: Record<string, any>) => {
    if (!trackActions) return
    
    const tipAction: TipAction = {
      id: `${componentName}-${Date.now()}`,
      action,
      metadata
    }
    
    actionsRef.current.push(tipAction)
    
    // Store in localStorage for persistence
    const existingActions = JSON.parse(
      localStorage.getItem('techlead-tip-actions') || '[]'
    )
    existingActions.push({
      ...tipAction,
      pathname,
      timestamp: new Date().toISOString()
    })
    
    // Keep only last 100 actions to prevent storage bloat
    if (existingActions.length > 100) {
      existingActions.splice(0, existingActions.length - 100)
    }
    
    localStorage.setItem('techlead-tip-actions', JSON.stringify(existingActions))
  }

  // Helper to add data attributes for tip targeting
  const getTipProps = (tipId: string, additionalData?: Record<string, string>) => {
    return {
      'data-tip-target': tipId,
      'data-component': componentName,
      ...additionalData
    }
  }

  // Mark tip as seen (for analytics)
  const markTipSeen = (tipId: string) => {
    const seenTips = JSON.parse(localStorage.getItem('techlead-tips-seen') || '[]')
    if (!seenTips.includes(tipId)) {
      seenTips.push(tipId)
      localStorage.setItem('techlead-tips-seen', JSON.stringify(seenTips))
    }
  }

  return {
    trackAction,
    getTipProps,
    markTipSeen,
    actions: actionsRef.current
  }
}

// Utility function to get tip targeting data attributes
export function getTipDataAttributes(config: {
  component?: string
  action?: string
  priority?: 'high' | 'medium' | 'low'
  metric?: string
  testId?: string
}) {
  const attributes: Record<string, string> = {}
  
  if (config.component) attributes['data-component'] = config.component
  if (config.action) attributes['data-action'] = config.action
  if (config.priority) attributes['data-priority'] = config.priority
  if (config.metric) attributes['data-metric'] = config.metric
  if (config.testId) attributes['data-testid'] = config.testId
  
  return attributes
}