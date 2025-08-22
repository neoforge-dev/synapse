"use client"

import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Play,
  ArrowRight,
  ArrowLeft,
  X,
  CheckCircle,
  Lightbulb,
  Zap,
  Target,
  Users,
  FileText,
  BarChart3,
  Sparkles
} from 'lucide-react'

interface TourStep {
  id: string
  title: string
  description: string
  target: string
  placement: 'top' | 'bottom' | 'left' | 'right' | 'center'
  action?: () => void
  nextButtonText?: string
  icon?: React.ComponentType<{ className?: string }>
  highlight?: boolean
  spotlightRadius?: number
}

interface ProductTourProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
  autoStart?: boolean
}

const tourSteps: TourStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to TechLead AutoPilot! 🚀',
    description: 'Your technical leadership automation platform is ready. Let\'s take a quick tour to show you how to transform your expertise into systematic business growth.',
    target: 'body',
    placement: 'center',
    nextButtonText: 'Start Tour',
    icon: Sparkles,
    highlight: false
  },
  {
    id: 'sidebar',
    title: 'Navigation Hub',
    description: 'Your command center. Use the sidebar to access all features. Try the keyboard shortcut ⌘B to toggle it, or ⌘K to search anything.',
    target: '[data-tour="sidebar"]',
    placement: 'right',
    icon: Target,
    highlight: true
  },
  {
    id: 'content-generation',
    title: 'Content Generation Engine',
    description: 'Create high-quality LinkedIn posts and articles with AI. This is where your expertise becomes systematic content that attracts clients.',
    target: '[data-tour="content-card"]',
    placement: 'top',
    icon: FileText,
    highlight: true,
    action: () => {}
  },
  {
    id: 'lead-detection',
    title: 'Lead Detection System',
    description: 'Automatically identify consultation opportunities from your content engagement. Every comment becomes a potential client.',
    target: '[data-tour="leads-card"]',
    placement: 'top',
    icon: Users,
    highlight: true
  },
  {
    id: 'search-feature',
    title: 'Universal Search',
    description: 'Find anything instantly with ⌘K. Search content, leads, analytics, or navigate to any page. Try it now!',
    target: '[data-tour="search-button"]',
    placement: 'bottom',
    icon: Zap,
    highlight: true,
    spotlightRadius: 50
  },
  {
    id: 'first-content',
    title: 'Create Your First Content',
    description: 'Ready to start? Click here to generate your first piece of content. We\'ll help you create something that attracts your ideal clients.',
    target: '[data-tour="generate-content"]',
    placement: 'left',
    icon: Play,
    highlight: true,
    nextButtonText: 'Generate Content',
    action: () => window.location.href = '/dashboard/content/generate'
  }
]

export function ProductTour({ isOpen, onClose, onComplete, autoStart = false }: ProductTourProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [isActive, setIsActive] = useState(false)
  const [targetElement, setTargetElement] = useState<HTMLElement | null>(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
  const overlayRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  const currentTourStep = tourSteps[currentStep]

  // Start tour
  useEffect(() => {
    if (isOpen && autoStart) {
      setIsActive(true)
    }
  }, [isOpen, autoStart])

  // Update target element and position when step changes
  useEffect(() => {
    if (!isActive || !currentTourStep) return

    const updateTarget = () => {
      const target = currentTourStep.target === 'body' 
        ? document.body 
        : document.querySelector(currentTourStep.target)
      
      setTargetElement(target as HTMLElement)
      
      if (target && target !== document.body) {
        const rect = target.getBoundingClientRect()
        const placement = currentTourStep.placement
        
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
          case 'center':
            x = window.innerWidth / 2
            y = window.innerHeight / 2
            break
        }
        
        setTooltipPosition({ x, y })
      } else {
        setTooltipPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 })
      }
    }

    updateTarget()
    window.addEventListener('resize', updateTarget)
    window.addEventListener('scroll', updateTarget)
    
    return () => {
      window.removeEventListener('resize', updateTarget)
      window.removeEventListener('scroll', updateTarget)
    }
  }, [currentStep, isActive, currentTourStep])

  // Handle keyboard navigation
  useEffect(() => {
    if (!isActive) return

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
          e.preventDefault()
          handleClose()
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isActive, currentStep])

  const handleNext = () => {
    if (currentTourStep.action) {
      currentTourStep.action()
      handleComplete()
      return
    }

    if (currentStep < tourSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleComplete()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSkip = () => {
    handleComplete()
  }

  const handleClose = () => {
    setIsActive(false)
    onClose()
  }

  const handleComplete = () => {
    setIsActive(false)
    onComplete()
    
    // Mark tour as completed in localStorage
    localStorage.setItem('techlead-tour-completed', 'true')
  }

  const getSpotlightStyle = () => {
    if (!targetElement || !currentTourStep.highlight || currentTourStep.target === 'body') {
      return {}
    }

    const rect = targetElement.getBoundingClientRect()
    const radius = currentTourStep.spotlightRadius || 8
    
    return {
      clipPath: `polygon(0% 0%, 0% 100%, ${rect.left - radius}px 100%, ${rect.left - radius}px ${rect.top - radius}px, ${rect.right + radius}px ${rect.top - radius}px, ${rect.right + radius}px ${rect.bottom + radius}px, ${rect.left - radius}px ${rect.bottom + radius}px, ${rect.left - radius}px 100%, 100% 100%, 100% 0%)`
    }
  }

  if (!isOpen || !isActive) return null

  const Icon = currentTourStep.icon || Lightbulb

  return createPortal(
    <div className="fixed inset-0 z-[9999]">
      {/* Overlay with spotlight effect */}
      <div 
        ref={overlayRef}
        className="absolute inset-0 bg-black/60 transition-all duration-300"
        style={getSpotlightStyle()}
      />
      
      {/* Highlighted element border */}
      {targetElement && currentTourStep.highlight && currentTourStep.target !== 'body' && (
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

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className={cn(
          "absolute bg-white rounded-xl shadow-2xl p-6 max-w-sm transform transition-all duration-300",
          currentTourStep.placement === 'center' ? 'max-w-md' : '',
          currentTourStep.placement === 'top' ? 'translate-x-[-50%] translate-y-[-100%]' : '',
          currentTourStep.placement === 'bottom' ? 'translate-x-[-50%]' : '',
          currentTourStep.placement === 'left' ? 'translate-x-[-100%] translate-y-[-50%]' : '',
          currentTourStep.placement === 'right' ? 'translate-y-[-50%]' : '',
          currentTourStep.placement === 'center' ? 'translate-x-[-50%] translate-y-[-50%]' : ''
        )}
        style={{
          left: tooltipPosition.x,
          top: tooltipPosition.y,
          zIndex: 10000
        }}
      >
        {/* Step indicator */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <Icon className="w-4 h-4 text-blue-600" />
            </div>
            <Badge variant="outline" className="text-xs">
              {currentStep + 1} of {tourSteps.length}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClose}
            className="p-1 h-6 w-6"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {currentTourStep.title}
          </h3>
          <p className="text-gray-600 leading-relaxed">
            {currentTourStep.description}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {currentStep > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handlePrevious}
                className="flex items-center space-x-1"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back</span>
              </Button>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSkip}
              className="text-gray-500"
            >
              Skip Tour
            </Button>
            <Button
              onClick={handleNext}
              className="flex items-center space-x-1"
            >
              <span>
                {currentTourStep.nextButtonText || 
                 (currentStep === tourSteps.length - 1 ? 'Finish' : 'Next')}
              </span>
              {currentStep === tourSteps.length - 1 ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Keyboard hints */}
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex items-center justify-center space-x-4 text-xs text-gray-500">
            <span>← → to navigate</span>
            <span>Esc to close</span>
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}

// Hook for managing tour state
export function useProductTour() {
  const [showTour, setShowTour] = useState(false)
  const [tourCompleted, setTourCompleted] = useState(false)

  useEffect(() => {
    const completed = localStorage.getItem('techlead-tour-completed')
    setTourCompleted(completed === 'true')
  }, [])

  const startTour = () => {
    setShowTour(true)
  }

  const closeTour = () => {
    setShowTour(false)
  }

  const completeTour = () => {
    setShowTour(false)
    setTourCompleted(true)
    localStorage.setItem('techlead-tour-completed', 'true')
  }

  const resetTour = () => {
    localStorage.removeItem('techlead-tour-completed')
    setTourCompleted(false)
  }

  return {
    showTour,
    tourCompleted,
    startTour,
    closeTour,
    completeTour,
    resetTour
  }
}