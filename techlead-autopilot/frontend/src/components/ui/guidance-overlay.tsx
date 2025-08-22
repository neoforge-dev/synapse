"use client"

import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Button } from './button'
import { Badge } from './badge'
import { cn } from '@/lib/utils'
import {
  X,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  ArrowRight,
  Lightbulb,
  Target,
  Zap
} from 'lucide-react'

interface GuidanceStep {
  id: string
  title: string
  description: string
  target: string | HTMLElement
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'center'
  action?: () => void | Promise<void>
  validation?: () => boolean | Promise<boolean>
  skipValidation?: boolean
  optional?: boolean
  nextButtonText?: string
  showProgress?: boolean
  highlightStyle?: 'spotlight' | 'outline' | 'pulse'
}

interface GuidanceOverlayProps {
  steps: GuidanceStep[]
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
  title: string
  description?: string
  allowSkip?: boolean
  persistent?: boolean
  className?: string
}

export function GuidanceOverlay({
  steps,
  isOpen,
  onClose,
  onComplete,
  title,
  description,
  allowSkip = true,
  persistent = false,
  className
}: GuidanceOverlayProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
  const [targetElement, setTargetElement] = useState<HTMLElement | null>(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
  const [isValidating, setIsValidating] = useState(false)
  const overlayRef = useRef<HTMLDivElement>(null)

  const currentGuidanceStep = steps[currentStep]

  // Update target element and position when step changes
  useEffect(() => {
    if (!isOpen || !currentGuidanceStep) return

    const updateTarget = () => {
      let target: HTMLElement | null = null
      
      if (typeof currentGuidanceStep.target === 'string') {
        target = document.querySelector(currentGuidanceStep.target)
      } else {
        target = currentGuidanceStep.target
      }
      
      setTargetElement(target)
      
      if (target && currentGuidanceStep.placement !== 'center') {
        const rect = target.getBoundingClientRect()
        const placement = currentGuidanceStep.placement || 'bottom'
        
        let x = 0, y = 0
        
        switch (placement) {
          case 'top':
            x = rect.left + rect.width / 2
            y = rect.top - 20
            break
          case 'bottom':
            x = rect.left + rect.width / 2
            y = rect.bottom + 20
            break
          case 'left':
            x = rect.left - 20
            y = rect.top + rect.height / 2
            break
          case 'right':
            x = rect.right + 20
            y = rect.top + rect.height / 2
            break
        }
        
        setTooltipPosition({ x, y })
      } else {
        // Center position
        setTooltipPosition({ 
          x: window.innerWidth / 2, 
          y: window.innerHeight / 2 
        })
      }
    }

    updateTarget()
    
    // Scroll target into view
    if (targetElement) {
      targetElement.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center',
        inline: 'center'
      })
    }

    window.addEventListener('resize', updateTarget)
    window.addEventListener('scroll', updateTarget)
    
    return () => {
      window.removeEventListener('resize', updateTarget)
      window.removeEventListener('scroll', updateTarget)
    }
  }, [currentStep, isOpen, currentGuidanceStep, targetElement])

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowRight':
        case 'Enter':
          e.preventDefault()
          handleNext()
          break
        case 'ArrowLeft':
          e.preventDefault()
          handlePrevious()
          break
        case 'Escape':
          if (allowSkip) {
            e.preventDefault()
            handleClose()
          }
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, currentStep, allowSkip])

  const handleNext = async () => {
    if (!currentGuidanceStep) return

    setIsValidating(true)

    try {
      // Execute step action if provided
      if (currentGuidanceStep.action) {
        await currentGuidanceStep.action()
      }

      // Validate step completion
      if (currentGuidanceStep.validation && !currentGuidanceStep.skipValidation) {
        const isValid = await currentGuidanceStep.validation()
        if (!isValid) {
          setIsValidating(false)
          return
        }
      }

      // Mark step as completed
      setCompletedSteps(prev => new Set(prev).add(currentStep))

      // Move to next step or complete
      if (currentStep < steps.length - 1) {
        setCurrentStep(currentStep + 1)
      } else {
        handleComplete()
      }
    } catch (error) {
      console.error('Guidance step error:', error)
    } finally {
      setIsValidating(false)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSkip = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleComplete()
    }
  }

  const handleClose = () => {
    setCurrentStep(0)
    setCompletedSteps(new Set())
    onClose()
  }

  const handleComplete = () => {
    setCurrentStep(0)
    setCompletedSteps(new Set())
    onComplete()
  }

  const getHighlightStyle = () => {
    if (!targetElement || !currentGuidanceStep.highlightStyle) {
      return {}
    }

    const rect = targetElement.getBoundingClientRect()
    const style = currentGuidanceStep.highlightStyle || 'spotlight'
    
    switch (style) {
      case 'spotlight':
        return {
          clipPath: `polygon(0% 0%, 0% 100%, ${rect.left - 8}px 100%, ${rect.left - 8}px ${rect.top - 8}px, ${rect.right + 8}px ${rect.top - 8}px, ${rect.right + 8}px ${rect.bottom + 8}px, ${rect.left - 8}px ${rect.bottom + 8}px, ${rect.left - 8}px 100%, 100% 100%, 100% 0%)`
        }
      default:
        return {}
    }
  }

  if (!isOpen) return null

  return createPortal(
    <div className="fixed inset-0 z-[9999]">
      {/* Overlay with spotlight effect */}
      <div 
        ref={overlayRef}
        className="absolute inset-0 bg-black/60 transition-all duration-300"
        style={getHighlightStyle()}
      />
      
      {/* Highlighted element border */}
      {targetElement && currentGuidanceStep.highlightStyle === 'outline' && (
        <div
          className="absolute border-2 border-blue-400 rounded-lg pointer-events-none transition-all duration-300"
          style={{
            left: targetElement.getBoundingClientRect().left - 4,
            top: targetElement.getBoundingClientRect().top - 4,
            width: targetElement.getBoundingClientRect().width + 8,
            height: targetElement.getBoundingClientRect().height + 8,
            boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.6)'
          }}
        />
      )}

      {/* Pulse effect */}
      {targetElement && currentGuidanceStep.highlightStyle === 'pulse' && (
        <div
          className="absolute border-4 border-blue-400 rounded-lg pointer-events-none animate-pulse"
          style={{
            left: targetElement.getBoundingClientRect().left - 8,
            top: targetElement.getBoundingClientRect().top - 8,
            width: targetElement.getBoundingClientRect().width + 16,
            height: targetElement.getBoundingClientRect().height + 16
          }}
        />
      )}

      {/* Guidance Tooltip */}
      <div
        className={cn(
          "absolute bg-white rounded-xl shadow-2xl max-w-md transform transition-all duration-300 border-2 border-blue-200",
          currentGuidanceStep.placement === 'center' ? 'max-w-lg' : '',
          currentGuidanceStep.placement === 'top' ? 'translate-x-[-50%] translate-y-[-100%]' : '',
          currentGuidanceStep.placement === 'bottom' ? 'translate-x-[-50%]' : '',
          currentGuidanceStep.placement === 'left' ? 'translate-x-[-100%] translate-y-[-50%]' : '',
          currentGuidanceStep.placement === 'right' ? 'translate-y-[-50%]' : '',
          currentGuidanceStep.placement === 'center' ? 'translate-x-[-50%] translate-y-[-50%]' : '',
          className
        )}
        style={{
          left: tooltipPosition.x,
          top: tooltipPosition.y,
          zIndex: 10000
        }}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <Target className="w-4 h-4 text-blue-600" />
              </div>
              <Badge variant="outline" className="text-xs">
                Step {currentStep + 1} of {steps.length}
              </Badge>
              {currentGuidanceStep.optional && (
                <Badge variant="secondary" className="text-xs">
                  Optional
                </Badge>
              )}
            </div>
            {allowSkip && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClose}
                className="p-1 h-6 w-6"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>

          {/* Progress Bar */}
          {currentGuidanceStep.showProgress !== false && (
            <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
              />
            </div>
          )}

          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {currentGuidanceStep.title}
          </h3>
          <p className="text-gray-600 leading-relaxed">
            {currentGuidanceStep.description}
          </p>
        </div>

        {/* Actions */}
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {currentStep > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePrevious}
                  disabled={isValidating}
                  className="flex items-center space-x-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span>Back</span>
                </Button>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              {currentGuidanceStep.optional && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleSkip}
                  disabled={isValidating}
                  className="text-gray-500"
                >
                  Skip
                </Button>
              )}
              <Button
                onClick={handleNext}
                disabled={isValidating}
                className="flex items-center space-x-1"
              >
                {isValidating ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>
                      {currentGuidanceStep.nextButtonText || 
                       (currentStep === steps.length - 1 ? 'Complete' : 'Next')}
                    </span>
                    {currentStep === steps.length - 1 ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Keyboard hints */}
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="flex items-center justify-center space-x-4 text-xs text-gray-500">
              <span>← → to navigate</span>
              <span>Enter to continue</span>
              {allowSkip && <span>Esc to close</span>}
            </div>
          </div>
        </div>

        {/* Arrow for non-center placements */}
        {currentGuidanceStep.placement !== 'center' && (
          <div
            className={cn(
              "absolute w-4 h-4 bg-white border-2 border-blue-200 transform rotate-45",
              currentGuidanceStep.placement === 'top' && 'bottom-[-8px] left-1/2 -translate-x-1/2 border-r-0 border-b-0',
              currentGuidanceStep.placement === 'bottom' && 'top-[-8px] left-1/2 -translate-x-1/2 border-l-0 border-t-0',
              currentGuidanceStep.placement === 'left' && 'right-[-8px] top-1/2 -translate-y-1/2 border-t-0 border-l-0',
              currentGuidanceStep.placement === 'right' && 'left-[-8px] top-1/2 -translate-y-1/2 border-b-0 border-r-0'
            )}
          />
        )}
      </div>
    </div>,
    document.body
  )
}

// Hook for managing guidance overlays
export function useGuidanceOverlay() {
  const [isOpen, setIsOpen] = useState(false)
  const [activeGuidance, setActiveGuidance] = useState<string | null>(null)

  const startGuidance = (guidanceId: string) => {
    setActiveGuidance(guidanceId)
    setIsOpen(true)
  }

  const closeGuidance = () => {
    setIsOpen(false)
    setActiveGuidance(null)
  }

  const completeGuidance = () => {
    if (activeGuidance) {
      // Mark guidance as completed in localStorage
      const completed = JSON.parse(localStorage.getItem('techlead-completed-guidance') || '[]')
      if (!completed.includes(activeGuidance)) {
        completed.push(activeGuidance)
        localStorage.setItem('techlead-completed-guidance', JSON.stringify(completed))
      }
    }
    closeGuidance()
  }

  const isGuidanceCompleted = (guidanceId: string) => {
    const completed = JSON.parse(localStorage.getItem('techlead-completed-guidance') || '[]')
    return completed.includes(guidanceId)
  }

  return {
    isOpen,
    activeGuidance,
    startGuidance,
    closeGuidance,
    completeGuidance,
    isGuidanceCompleted
  }
}