"use client"

import React, { useRef, useEffect } from 'react'
import { useTooltip } from './tooltip-provider'
import { cn } from '@/lib/utils'

interface FeatureTooltipProps {
  id: string
  title?: string
  content: string
  type?: 'info' | 'help' | 'warning' | 'tip' | 'feature'
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'auto'
  trigger?: 'hover' | 'click' | 'focus' | 'manual'
  delay?: number
  showOnce?: boolean
  learnMoreUrl?: string
  disabled?: boolean
  children: React.ReactNode
  className?: string
}

export function FeatureTooltip({
  id,
  title,
  content,
  type = 'feature',
  placement = 'auto',
  trigger = 'hover',
  delay = 500,
  showOnce = true,
  learnMoreUrl,
  disabled = false,
  children,
  className
}: FeatureTooltipProps) {
  const elementRef = useRef<HTMLDivElement>(null)
  const { showTooltip, hideTooltip, isTooltipVisible } = useTooltip()
  const hoverTimeoutRef = useRef<NodeJS.Timeout>()
  const clickTimeoutRef = useRef<NodeJS.Timeout>()

  const handleShow = () => {
    if (disabled || !elementRef.current) return
    
    showTooltip(id, elementRef.current, {
      title,
      content,
      type,
      placement,
      trigger,
      delay,
      showOnce,
      learnMoreUrl
    })
  }

  const handleHide = () => {
    hideTooltip(id)
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
    }
    if (clickTimeoutRef.current) {
      clearTimeout(clickTimeoutRef.current)
    }
  }

  const handleMouseEnter = () => {
    if (trigger !== 'hover' || disabled) return
    
    hoverTimeoutRef.current = setTimeout(handleShow, delay)
  }

  const handleMouseLeave = () => {
    if (trigger !== 'hover') return
    
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
    }
    
    // Small delay before hiding to prevent flickering
    setTimeout(handleHide, 100)
  }

  const handleClick = () => {
    if (trigger !== 'click' || disabled) return
    
    if (isTooltipVisible(id)) {
      handleHide()
    } else {
      handleShow()
    }
  }

  const handleFocus = () => {
    if (trigger !== 'focus' || disabled) return
    
    handleShow()
  }

  const handleBlur = () => {
    if (trigger !== 'focus') return
    
    handleHide()
  }

  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current)
      }
      if (clickTimeoutRef.current) {
        clearTimeout(clickTimeoutRef.current)
      }
    }
  }, [])

  // Manual trigger support
  useEffect(() => {
    if (trigger === 'manual' && !disabled) {
      // Allow manual control via ref or external state
      const element = elementRef.current
      if (element && element.dataset.showTooltip === 'true') {
        handleShow()
      }
    }
  }, [trigger, disabled])

  return (
    <div
      ref={elementRef}
      className={cn("relative inline-block", className)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      onFocus={handleFocus}
      onBlur={handleBlur}
      data-tooltip-id={id}
      role={trigger === 'click' ? 'button' : undefined}
      tabIndex={trigger === 'click' ? 0 : undefined}
      aria-describedby={isTooltipVisible(id) ? `tooltip-${id}` : undefined}
    >
      {children}
    </div>
  )
}

// Specialized tooltip components for common use cases

interface FormFieldTooltipProps extends Omit<FeatureTooltipProps, 'type' | 'children'> {
  children: React.ReactElement
  error?: string
  helpText?: string
}

export function FormFieldTooltip({
  error,
  helpText,
  content,
  ...props
}: FormFieldTooltipProps) {
  const tooltipContent = error || helpText || content
  const tooltipType = error ? 'warning' : 'help'

  return (
    <FeatureTooltip
      {...props}
      content={tooltipContent}
      type={tooltipType}
      trigger="focus"
      showOnce={false}
    >
      {React.cloneElement(props.children, {
        className: cn(
          props.children.props.className,
          error && "border-red-300 focus:border-red-500 focus:ring-red-500"
        ),
        'aria-invalid': error ? 'true' : undefined,
        'aria-describedby': error ? `error-${props.id}` : undefined
      })}
    </FeatureTooltip>
  )
}

interface ButtonTooltipProps extends Omit<FeatureTooltipProps, 'children'> {
  children: React.ReactElement
  shortcut?: string
  disabled?: boolean
}

export function ButtonTooltip({
  shortcut,
  content,
  disabled,
  ...props
}: ButtonTooltipProps) {
  const tooltipContent = shortcut ? `${content} (${shortcut})` : content

  return (
    <FeatureTooltip
      {...props}
      content={tooltipContent}
      type="info"
      trigger="hover"
      delay={300}
      disabled={disabled}
    >
      {props.children}
    </FeatureTooltip>
  )
}

interface MetricTooltipProps extends Omit<FeatureTooltipProps, 'type' | 'children'> {
  children: React.ReactNode
  metric: string
  calculation?: string
  trend?: 'up' | 'down' | 'stable'
}

export function MetricTooltip({
  metric,
  calculation,
  trend,
  content,
  ...props
}: MetricTooltipProps) {
  let tooltipContent = content
  
  if (calculation) {
    tooltipContent += `\n\nCalculation: ${calculation}`
  }
  
  if (trend) {
    const trendText = {
      up: '📈 Trending up',
      down: '📉 Trending down',
      stable: '➡️ Stable'
    }[trend]
    tooltipContent += `\n\n${trendText}`
  }

  return (
    <FeatureTooltip
      {...props}
      content={tooltipContent}
      type="info"
      trigger="hover"
      delay={200}
      showOnce={false}
    >
      <div className="cursor-help border-b border-dashed border-gray-400">
        {props.children}
      </div>
    </FeatureTooltip>
  )
}

interface NavigationTooltipProps extends Omit<FeatureTooltipProps, 'type'> {
  isNewFeature?: boolean
  keyboardShortcut?: string
}

export function NavigationTooltip({
  isNewFeature,
  keyboardShortcut,
  content,
  ...props
}: NavigationTooltipProps) {
  let tooltipContent = content
  
  if (keyboardShortcut) {
    tooltipContent += `\n\nShortcut: ${keyboardShortcut}`
  }
  
  if (isNewFeature) {
    tooltipContent = `🆕 ${tooltipContent}`
  }

  return (
    <FeatureTooltip
      {...props}
      content={tooltipContent}
      type={isNewFeature ? 'feature' : 'info'}
      trigger="hover"
      delay={400}
    >
      {props.children}
    </FeatureTooltip>
  )
}