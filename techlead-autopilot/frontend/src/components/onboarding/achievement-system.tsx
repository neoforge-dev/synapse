"use client"

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import {
  Trophy,
  Star,
  Zap,
  Target,
  Crown,
  Medal,
  Award,
  Sparkles,
  TrendingUp,
  Users,
  FileText,
  BarChart3,
  CheckCircle,
  Lock,
  Gift
} from 'lucide-react'

interface Achievement {
  id: string
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  category: 'getting-started' | 'content-creator' | 'lead-generator' | 'power-user' | 'milestone'
  tier: 'bronze' | 'silver' | 'gold' | 'platinum'
  points: number
  requirement: {
    type: 'count' | 'streak' | 'value' | 'action'
    target: number | string
    metric: string
  }
  reward?: {
    type: 'feature' | 'badge' | 'content'
    description: string
  }
  isUnlocked?: boolean
  progress?: number
  unlockedAt?: string
}

interface AchievementSystemProps {
  className?: string
  onAchievementUnlocked?: (achievement: Achievement) => void
}

const achievements: Achievement[] = [
  // Getting Started
  {
    id: 'first-login',
    title: 'Welcome Aboard!',
    description: 'Logged into TechLead AutoPilot for the first time',
    icon: Star,
    category: 'getting-started',
    tier: 'bronze',
    points: 10,
    requirement: { type: 'action', target: 'login', metric: 'first_login' },
    reward: { type: 'badge', description: 'Pioneer Badge' }
  },
  {
    id: 'profile-complete',
    title: 'Professional Setup',
    description: 'Completed your professional profile',
    icon: Target,
    category: 'getting-started',
    tier: 'bronze',
    points: 25,
    requirement: { type: 'action', target: 'profile_complete', metric: 'profile_completion' },
    reward: { type: 'feature', description: 'Enhanced content personalization' }
  },
  {
    id: 'tour-complete',
    title: 'Platform Explorer',
    description: 'Completed the product tour',
    icon: Sparkles,
    category: 'getting-started',
    tier: 'bronze',
    points: 15,
    requirement: { type: 'action', target: 'tour_complete', metric: 'tour_completion' }
  },

  // Content Creator
  {
    id: 'first-content',
    title: 'Content Creator',
    description: 'Generated your first piece of content',
    icon: FileText,
    category: 'content-creator',
    tier: 'bronze',
    points: 50,
    requirement: { type: 'count', target: 1, metric: 'content_generated' },
    reward: { type: 'content', description: 'Advanced content templates unlocked' }
  },
  {
    id: 'content-streak-7',
    title: 'Weekly Warrior',
    description: 'Generated content for 7 consecutive days',
    icon: Zap,
    category: 'content-creator',
    tier: 'silver',
    points: 100,
    requirement: { type: 'streak', target: 7, metric: 'daily_content' },
    reward: { type: 'feature', description: 'Auto-scheduling feature' }
  },
  {
    id: 'content-viral',
    title: 'Viral Hit',
    description: 'Created content with 1000+ views',
    icon: TrendingUp,
    category: 'content-creator',
    tier: 'gold',
    points: 200,
    requirement: { type: 'value', target: 1000, metric: 'max_content_views' },
    reward: { type: 'badge', description: 'Viral Creator Badge' }
  },
  {
    id: 'content-master',
    title: 'Content Master',
    description: 'Generated 50 pieces of content',
    icon: Crown,
    category: 'content-creator',
    tier: 'platinum',
    points: 500,
    requirement: { type: 'count', target: 50, metric: 'content_generated' },
    reward: { type: 'feature', description: 'AI writing assistant upgrade' }
  },

  // Lead Generator
  {
    id: 'first-lead',
    title: 'Lead Magnet',
    description: 'Generated your first qualified lead',
    icon: Users,
    category: 'lead-generator',
    tier: 'bronze',
    points: 75,
    requirement: { type: 'count', target: 1, metric: 'leads_generated' },
    reward: { type: 'feature', description: 'Lead scoring insights' }
  },
  {
    id: 'high-value-lead',
    title: 'Big Fish',
    description: 'Generated a lead worth €5000+',
    icon: Medal,
    category: 'lead-generator',
    tier: 'silver',
    points: 150,
    requirement: { type: 'value', target: 5000, metric: 'max_lead_value' },
    reward: { type: 'badge', description: 'High-Value Lead Hunter' }
  },
  {
    id: 'lead-conversion',
    title: 'Deal Closer',
    description: 'Converted a lead into a paying client',
    icon: Award,
    category: 'lead-generator',
    tier: 'gold',
    points: 300,
    requirement: { type: 'count', target: 1, metric: 'leads_converted' },
    reward: { type: 'feature', description: 'Advanced conversion tracking' }
  },
  {
    id: 'pipeline-value',
    title: 'Revenue Generator',
    description: 'Built a pipeline worth €25,000+',
    icon: Trophy,
    category: 'lead-generator',
    tier: 'platinum',
    points: 750,
    requirement: { type: 'value', target: 25000, metric: 'total_pipeline_value' },
    reward: { type: 'badge', description: 'Revenue Champion' }
  },

  // Power User
  {
    id: 'keyboard-ninja',
    title: 'Keyboard Ninja',
    description: 'Used 10 different keyboard shortcuts',
    icon: Zap,
    category: 'power-user',
    tier: 'silver',
    points: 100,
    requirement: { type: 'count', target: 10, metric: 'shortcuts_used' },
    reward: { type: 'feature', description: 'Custom shortcut configuration' }
  },
  {
    id: 'analytics-explorer',
    title: 'Data Explorer',
    description: 'Viewed analytics dashboard 25 times',
    icon: BarChart3,
    category: 'power-user',
    tier: 'silver',
    points: 75,
    requirement: { type: 'count', target: 25, metric: 'analytics_views' },
    reward: { type: 'feature', description: 'Advanced analytics filters' }
  },

  // Milestones
  {
    id: 'point-collector-1000',
    title: 'Point Collector',
    description: 'Earned 1,000 achievement points',
    icon: Star,
    category: 'milestone',
    tier: 'gold',
    points: 100,
    requirement: { type: 'value', target: 1000, metric: 'total_points' },
    reward: { type: 'badge', description: 'Point Master Badge' }
  },
  {
    id: 'platform-champion',
    title: 'Platform Champion',
    description: 'Unlocked 15 achievements',
    icon: Crown,
    category: 'milestone',
    tier: 'platinum',
    points: 200,
    requirement: { type: 'count', target: 15, metric: 'achievements_unlocked' },
    reward: { type: 'badge', description: 'Champion Status' }
  }
]

const tierConfig = {
  bronze: { color: 'bg-amber-600', textColor: 'text-amber-600', borderColor: 'border-amber-200' },
  silver: { color: 'bg-gray-500', textColor: 'text-gray-500', borderColor: 'border-gray-200' },
  gold: { color: 'bg-yellow-500', textColor: 'text-yellow-500', borderColor: 'border-yellow-200' },
  platinum: { color: 'bg-purple-600', textColor: 'text-purple-600', borderColor: 'border-purple-200' }
}

const categoryConfig = {
  'getting-started': { label: 'Getting Started', icon: Target },
  'content-creator': { label: 'Content Creator', icon: FileText },
  'lead-generator': { label: 'Lead Generator', icon: Users },
  'power-user': { label: 'Power User', icon: Zap },
  'milestone': { label: 'Milestones', icon: Trophy }
}

export function AchievementSystem({ className, onAchievementUnlocked }: AchievementSystemProps) {
  const [unlockedAchievements, setUnlockedAchievements] = useState<Set<string>>(new Set())
  const [userStats, setUserStats] = useState({
    content_generated: 0,
    leads_generated: 0,
    total_pipeline_value: 0,
    achievements_unlocked: 0,
    total_points: 0,
    analytics_views: 0,
    shortcuts_used: 0
  })
  const [selectedCategory, setSelectedCategory] = useState<string>('getting-started')
  const [showUnlocked, setShowUnlocked] = useState(false)

  // Load user stats and achievements from localStorage
  useEffect(() => {
    const savedAchievements = localStorage.getItem('techlead-achievements')
    const savedStats = localStorage.getItem('techlead-user-stats')
    
    if (savedAchievements) {
      setUnlockedAchievements(new Set(JSON.parse(savedAchievements)))
    }
    
    if (savedStats) {
      setUserStats(JSON.parse(savedStats))
    }
  }, [])

  // Check for new achievements when stats change
  useEffect(() => {
    achievements.forEach(achievement => {
      if (unlockedAchievements.has(achievement.id)) return

      const isUnlocked = checkAchievementRequirement(achievement, userStats)
      if (isUnlocked) {
        unlockAchievement(achievement)
      }
    })
  }, [userStats, unlockedAchievements])

  const checkAchievementRequirement = (achievement: Achievement, stats: any): boolean => {
    const { type, target, metric } = achievement.requirement
    const currentValue = stats[metric] || 0

    switch (type) {
      case 'count':
      case 'value':
        return currentValue >= target
      case 'action':
        return currentValue === target || currentValue === true
      case 'streak':
        return currentValue >= target
      default:
        return false
    }
  }

  const unlockAchievement = (achievement: Achievement) => {
    const newUnlocked = new Set(unlockedAchievements)
    newUnlocked.add(achievement.id)
    setUnlockedAchievements(newUnlocked)

    // Update stats
    const newStats = {
      ...userStats,
      achievements_unlocked: newUnlocked.size,
      total_points: userStats.total_points + achievement.points
    }
    setUserStats(newStats)

    // Save to localStorage
    localStorage.setItem('techlead-achievements', JSON.stringify([...newUnlocked]))
    localStorage.setItem('techlead-user-stats', JSON.stringify(newStats))

    onAchievementUnlocked?.(achievement)
  }

  const getAchievementProgress = (achievement: Achievement): number => {
    const { type, target, metric } = achievement.requirement
    const currentValue = userStats[metric] || 0

    if (unlockedAchievements.has(achievement.id)) return 100

    switch (type) {
      case 'count':
      case 'value':
        return Math.min((currentValue / (target as number)) * 100, 100)
      case 'streak':
        return Math.min((currentValue / (target as number)) * 100, 100)
      default:
        return 0
    }
  }

  const filteredAchievements = achievements.filter(achievement => {
    if (showUnlocked) {
      return unlockedAchievements.has(achievement.id)
    }
    return achievement.category === selectedCategory
  })

  const totalPoints = Array.from(unlockedAchievements)
    .map(id => achievements.find(a => a.id === id)?.points || 0)
    .reduce((sum, points) => sum + points, 0)

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <Trophy className="w-5 h-5 text-yellow-500" />
              <span>Achievements</span>
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              Track your progress and unlock rewards
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-yellow-600">{totalPoints}</div>
            <div className="text-xs text-gray-500">total points</div>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-semibold text-gray-900">{unlockedAchievements.size}</div>
            <div className="text-xs text-gray-500">Unlocked</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-semibold text-gray-900">{achievements.length - unlockedAchievements.size}</div>
            <div className="text-xs text-gray-500">Remaining</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-semibold text-gray-900">{userStats.content_generated}</div>
            <div className="text-xs text-gray-500">Content</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-semibold text-gray-900">{userStats.leads_generated}</div>
            <div className="text-xs text-gray-500">Leads</div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Category Filters */}
        <div className="flex flex-wrap gap-2 mb-6">
          {Object.entries(categoryConfig).map(([category, config]) => {
            const Icon = config.icon
            const isSelected = selectedCategory === category && !showUnlocked
            
            return (
              <Button
                key={category}
                variant={isSelected ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  setSelectedCategory(category)
                  setShowUnlocked(false)
                }}
                className="flex items-center space-x-1"
              >
                <Icon className="w-3 h-3" />
                <span>{config.label}</span>
              </Button>
            )
          })}
          <Button
            variant={showUnlocked ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowUnlocked(!showUnlocked)}
            className="flex items-center space-x-1"
          >
            <CheckCircle className="w-3 h-3" />
            <span>Unlocked ({unlockedAchievements.size})</span>
          </Button>
        </div>

        {/* Achievements Grid */}
        <div className="grid gap-4">
          {filteredAchievements.map((achievement) => {
            const Icon = achievement.icon
            const isUnlocked = unlockedAchievements.has(achievement.id)
            const progress = getAchievementProgress(achievement)
            const tierConfig_ = tierConfig[achievement.tier]

            return (
              <div
                key={achievement.id}
                className={cn(
                  "p-4 border rounded-lg transition-all",
                  isUnlocked 
                    ? `bg-gradient-to-r from-yellow-50 to-amber-50 ${tierConfig_.borderColor} border-2` 
                    : "border-gray-200 hover:border-gray-300"
                )}
              >
                <div className="flex items-start space-x-4">
                  {/* Icon */}
                  <div className={cn(
                    "w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0",
                    isUnlocked ? tierConfig_.color : "bg-gray-100"
                  )}>
                    {isUnlocked ? (
                      <Icon className="w-6 h-6 text-white" />
                    ) : (
                      <Lock className="w-6 h-6 text-gray-400" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className={cn(
                        "font-medium",
                        isUnlocked ? "text-gray-900" : "text-gray-600"
                      )}>
                        {achievement.title}
                      </h3>
                      <Badge 
                        variant="outline" 
                        className={cn("text-xs", tierConfig_.textColor)}
                      >
                        {achievement.tier}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {achievement.points} pts
                      </Badge>
                    </div>
                    
                    <p className={cn(
                      "text-sm mb-3",
                      isUnlocked ? "text-gray-700" : "text-gray-500"
                    )}>
                      {achievement.description}
                    </p>

                    {/* Progress Bar */}
                    {!isUnlocked && progress > 0 && (
                      <div className="mb-3">
                        <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                          <span>Progress</span>
                          <span>{Math.round(progress)}%</span>
                        </div>
                        <Progress value={progress} className="h-1" />
                      </div>
                    )}

                    {/* Reward */}
                    {achievement.reward && (
                      <div className="flex items-center space-x-2 text-xs">
                        <Gift className="w-3 h-3 text-blue-500" />
                        <span className="text-blue-600">{achievement.reward.description}</span>
                      </div>
                    )}
                  </div>

                  {/* Status */}
                  {isUnlocked && (
                    <div className="flex-shrink-0">
                      <CheckCircle className={cn("w-6 h-6", tierConfig_.textColor)} />
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {filteredAchievements.length === 0 && (
          <div className="text-center py-8">
            <Trophy className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">No achievements in this category yet.</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}