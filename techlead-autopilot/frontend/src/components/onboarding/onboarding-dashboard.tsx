"use client"

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { ProductTour, useProductTour } from './product-tour'
import { WelcomeChecklist } from './welcome-checklist'
import { SampleDataGenerator } from './sample-data-generator'
import { AchievementSystem } from './achievement-system'
import { useContextualTips } from './contextual-tips'
import { cn } from '@/lib/utils'
import {
  Rocket,
  CheckCircle,
  Clock,
  Trophy,
  Lightbulb,
  Play,
  Star,
  Target,
  Zap,
  TrendingUp
} from 'lucide-react'

interface OnboardingDashboardProps {
  className?: string
  onComplete?: () => void
}

interface OnboardingMetrics {
  tourCompleted: boolean
  checklistProgress: number
  sampleDataGenerated: boolean
  achievementsUnlocked: number
  tipsEnabled: boolean
  totalProgress: number
}

export function OnboardingDashboard({ className, onComplete }: OnboardingDashboardProps) {
  const [metrics, setMetrics] = useState<OnboardingMetrics>({
    tourCompleted: false,
    checklistProgress: 0,
    sampleDataGenerated: false,
    achievementsUnlocked: 0,
    tipsEnabled: true,
    totalProgress: 0
  })
  const [activeTab, setActiveTab] = useState<'tour' | 'checklist' | 'data' | 'achievements'>('tour')
  
  const { showTour, tourCompleted, startTour, completeTour } = useProductTour()
  const { isEnabled: tipsEnabled, toggleTips } = useContextualTips()

  // Calculate onboarding metrics
  useEffect(() => {
    const calculateMetrics = () => {
      // Check tour completion
      const tourComplete = localStorage.getItem('techlead-tour-completed') === 'true'
      
      // Check checklist progress
      const completedItems = JSON.parse(localStorage.getItem('techlead-checklist-completed') || '[]')
      const checklistProgress = (completedItems.length / 10) * 100 // Assuming 10 total items
      
      // Check sample data
      const generatedSets = JSON.parse(localStorage.getItem('sample-data-generated') || '[]')
      const sampleDataComplete = generatedSets.length >= 3
      
      // Check achievements
      const achievements = JSON.parse(localStorage.getItem('techlead-achievements') || '[]')
      const achievementCount = achievements.length
      
      // Calculate total progress
      const components = [
        tourComplete ? 100 : 0,
        checklistProgress,
        sampleDataComplete ? 100 : 0,
        Math.min((achievementCount / 5) * 100, 100), // Cap at 5 achievements for 100%
        tipsEnabled ? 100 : 0
      ]
      const totalProgress = components.reduce((sum, val) => sum + val, 0) / components.length

      setMetrics({
        tourCompleted: tourComplete,
        checklistProgress: Math.round(checklistProgress),
        sampleDataGenerated: sampleDataComplete,
        achievementsUnlocked: achievementCount,
        tipsEnabled,
        totalProgress: Math.round(totalProgress)
      })

      // Auto-complete when everything is done
      if (totalProgress >= 90 && onComplete) {
        onComplete()
      }
    }

    calculateMetrics()
    const interval = setInterval(calculateMetrics, 2000) // Update every 2 seconds
    return () => clearInterval(interval)
  }, [tipsEnabled, onComplete])

  const getProgressColor = (progress: number) => {
    if (progress >= 80) return 'text-green-600'
    if (progress >= 60) return 'text-yellow-600'
    return 'text-blue-600'
  }

  const getProgressBadge = (progress: number) => {
    if (progress >= 90) return { text: 'Complete', variant: 'default' as const }
    if (progress >= 60) return { text: 'Almost There', variant: 'secondary' as const }
    if (progress >= 30) return { text: 'In Progress', variant: 'outline' as const }
    return { text: 'Getting Started', variant: 'outline' as const }
  }

  const tabs = [
    { id: 'tour', name: 'Product Tour', icon: Play, completed: metrics.tourCompleted },
    { id: 'checklist', name: 'Checklist', icon: CheckCircle, completed: metrics.checklistProgress === 100 },
    { id: 'data', name: 'Sample Data', icon: Target, completed: metrics.sampleDataGenerated },
    { id: 'achievements', name: 'Achievements', icon: Trophy, completed: metrics.achievementsUnlocked >= 3 }
  ]

  return (
    <div className={cn("w-full max-w-6xl mx-auto", className)}>
      {/* Header */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <Rocket className="w-5 h-5 text-blue-500" />
                <span>Welcome to TechLead AutoPilot</span>
              </CardTitle>
              <p className="text-sm text-gray-600 mt-1">
                Complete these steps to unlock your technical leadership potential
              </p>
            </div>
            <div className="text-right">
              <div className={cn("text-3xl font-bold", getProgressColor(metrics.totalProgress))}>
                {metrics.totalProgress}%
              </div>
              <Badge {...getProgressBadge(metrics.totalProgress)}>
                {getProgressBadge(metrics.totalProgress).text}
              </Badge>
            </div>
          </div>
          
          {/* Overall Progress */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span>Overall Progress</span>
              <span>{metrics.totalProgress}% complete</span>
            </div>
            <Progress value={metrics.totalProgress} className="h-2" />
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                {metrics.tourCompleted ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <Clock className="w-4 h-4 text-blue-500" />
                )}
              </div>
              <div className="text-sm font-medium text-gray-900">
                {metrics.tourCompleted ? 'Tour Complete' : 'Tour Pending'}
              </div>
            </div>
            
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <div className="text-lg font-semibold text-green-600">{metrics.checklistProgress}%</div>
              <div className="text-sm text-gray-600">Checklist</div>
            </div>
            
            <div className="text-center p-3 bg-purple-50 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <Trophy className="w-4 h-4 text-purple-500" />
              </div>
              <div className="text-sm font-medium text-gray-900">
                {metrics.achievementsUnlocked} Achievements
              </div>
            </div>
            
            <div className="text-center p-3 bg-yellow-50 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <Lightbulb className="w-4 h-4 text-yellow-500" />
              </div>
              <div className="text-sm font-medium text-gray-900">
                {metrics.tipsEnabled ? 'Tips Active' : 'Tips Off'}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <Button
              key={tab.id}
              variant={activeTab === tab.id ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab(tab.id as any)}
              className="flex items-center space-x-2"
            >
              <Icon className="w-4 h-4" />
              <span>{tab.name}</span>
              {tab.completed && (
                <CheckCircle className="w-3 h-3 text-green-500 ml-1" />
              )}
            </Button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'tour' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Play className="w-5 h-5 text-blue-500" />
                <span>Interactive Product Tour</span>
                {metrics.tourCompleted && <CheckCircle className="w-4 h-4 text-green-500" />}
              </CardTitle>
              <p className="text-sm text-gray-600">
                Get familiar with the platform features and learn keyboard shortcuts
              </p>
            </CardHeader>
            <CardContent>
              {metrics.tourCompleted ? (
                <div className="text-center py-8">
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Tour Complete!</h3>
                  <p className="text-gray-600 mb-4">
                    You've successfully completed the product tour. Ready to explore?
                  </p>
                  <Button onClick={startTour} variant="outline">
                    Take Tour Again
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Play className="w-8 h-8 text-blue-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Ready for Your Tour?</h3>
                  <p className="text-gray-600 mb-4">
                    Take a guided tour to learn about key features and how to get the most from the platform.
                  </p>
                  <Button onClick={startTour}>
                    <Play className="w-4 h-4 mr-2" />
                    Start Product Tour
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === 'checklist' && (
          <WelcomeChecklist 
            onItemComplete={() => {
              // Metrics will be recalculated by the useEffect
            }}
          />
        )}

        {activeTab === 'data' && (
          <SampleDataGenerator 
            onAllGenerated={() => {
              // Metrics will be recalculated by the useEffect
            }}
          />
        )}

        {activeTab === 'achievements' && (
          <AchievementSystem 
            onAchievementUnlocked={() => {
              // Metrics will be recalculated by the useEffect
            }}
          />
        )}
      </div>

      {/* Completion Celebration */}
      {metrics.totalProgress >= 90 && (
        <Card className="mt-6 bg-gradient-to-r from-green-50 to-blue-50 border-green-200">
          <CardContent className="p-6">
            <div className="text-center">
              <div className="flex items-center justify-center space-x-2 mb-4">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-green-600" />
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <Star className="w-6 h-6 text-blue-600" />
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                  <Trophy className="w-6 h-6 text-purple-600" />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Congratulations! 🎉</h2>
              <p className="text-gray-700 mb-4">
                You've completed the onboarding process. Your technical leadership automation system is ready to generate business value!
              </p>
              <div className="flex items-center justify-center space-x-4">
                <Button asChild>
                  <a href="/dashboard/content/generate">
                    <Zap className="w-4 h-4 mr-2" />
                    Generate Your First Content
                  </a>
                </Button>
                <Button variant="outline" asChild>
                  <a href="/dashboard">
                    View Dashboard
                  </a>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Product Tour Component */}
      <ProductTour
        isOpen={showTour}
        onClose={() => {}}
        onComplete={completeTour}
        autoStart={true}
      />
    </div>
  )
}