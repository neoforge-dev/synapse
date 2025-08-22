"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  Search,
  Book,
  HelpCircle,
  FileText,
  Video,
  MessageCircle,
  ExternalLink,
  ChevronRight,
  Star,
  Clock,
  Users,
  Lightbulb,
  Zap,
  Target,
  BarChart3,
  Settings,
  Shield,
  Rocket,
  Heart,
  TrendingUp
} from 'lucide-react'

interface HelpArticle {
  id: string
  title: string
  description: string
  content?: string
  category: 'getting-started' | 'content-creation' | 'lead-management' | 'analytics' | 'settings' | 'troubleshooting'
  type: 'article' | 'video' | 'faq' | 'guide'
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  readTime: string
  popularity: number
  lastUpdated: string
  tags: string[]
  icon?: React.ComponentType<{ className?: string }>
  href?: string
  isExternal?: boolean
}

interface HelpCenterProps {
  className?: string
  initialSearchQuery?: string
  showCategories?: boolean
}

const helpArticles: HelpArticle[] = [
  // Getting Started
  {
    id: 'quick-start-guide',
    title: 'Quick Start Guide',
    description: 'Get up and running with TechLead AutoPilot in 5 minutes',
    category: 'getting-started',
    type: 'guide',
    difficulty: 'beginner',
    readTime: '5 min',
    popularity: 95,
    lastUpdated: '2024-01-15',
    tags: ['setup', 'beginner', 'onboarding'],
    icon: Rocket,
    content: `# Quick Start Guide

Welcome to TechLead AutoPilot! This guide will help you get started in just 5 minutes.

## Step 1: Complete Your Profile
Navigate to Settings → Profile and fill in your technical background, current role, and expertise areas. This helps our AI generate more personalized content.

## Step 2: Take the Product Tour
Click the "Start Tour" button to learn about key features and navigation shortcuts.

## Step 3: Generate Your First Content
Go to Content → Generate New and create your first LinkedIn post about your technical leadership experience.

## Step 4: Review and Schedule
Edit your generated content, then schedule it for optimal engagement times (Tuesday/Thursday 6:30 AM).

That's it! You're ready to start building your technical leadership brand systematically.`
  },
  {
    id: 'platform-overview',
    title: 'Platform Overview',
    description: 'Understanding the core components and workflow',
    category: 'getting-started',
    type: 'article',
    difficulty: 'beginner',
    readTime: '8 min',
    popularity: 88,
    lastUpdated: '2024-01-12',
    tags: ['overview', 'features', 'workflow'],
    icon: Book
  },
  {
    id: 'keyboard-shortcuts',
    title: 'Keyboard Shortcuts Reference',
    description: 'Speed up your workflow with powerful keyboard shortcuts',
    category: 'getting-started',
    type: 'article',
    difficulty: 'intermediate',
    readTime: '3 min',
    popularity: 76,
    lastUpdated: '2024-01-10',
    tags: ['shortcuts', 'productivity', 'navigation'],
    icon: Zap
  },

  // Content Creation
  {
    id: 'content-best-practices',
    title: 'Content Creation Best Practices',
    description: 'Write compelling technical content that attracts clients',
    category: 'content-creation',
    type: 'guide',
    difficulty: 'intermediate',
    readTime: '12 min',
    popularity: 92,
    lastUpdated: '2024-01-14',
    tags: ['content', 'writing', 'engagement', 'best-practices'],
    icon: FileText
  },
  {
    id: 'content-templates',
    title: 'Understanding Content Templates',
    description: 'Learn about different content types and when to use them',
    category: 'content-creation',
    type: 'article',
    difficulty: 'beginner',
    readTime: '6 min',
    popularity: 84,
    lastUpdated: '2024-01-11',
    tags: ['templates', 'content-types', 'strategy'],
    icon: Target
  },
  {
    id: 'content-scheduling',
    title: 'Optimal Content Scheduling',
    description: 'Maximize engagement with strategic timing',
    category: 'content-creation',
    type: 'article',
    difficulty: 'intermediate',
    readTime: '7 min',
    popularity: 79,
    lastUpdated: '2024-01-09',
    tags: ['scheduling', 'timing', 'engagement'],
    icon: Clock
  },

  // Lead Management
  {
    id: 'lead-scoring-explained',
    title: 'Understanding Lead Scoring',
    description: 'How our AI identifies high-value consultation opportunities',
    category: 'lead-management',
    type: 'article',
    difficulty: 'intermediate',
    readTime: '10 min',
    popularity: 89,
    lastUpdated: '2024-01-13',
    tags: ['leads', 'scoring', 'ai', 'qualification'],
    icon: Users
  },
  {
    id: 'lead-follow-up-strategies',
    title: 'Lead Follow-up Strategies',
    description: 'Convert prospects into paying clients effectively',
    category: 'lead-management',
    type: 'guide',
    difficulty: 'advanced',
    readTime: '15 min',
    popularity: 87,
    lastUpdated: '2024-01-08',
    tags: ['follow-up', 'conversion', 'sales', 'strategy'],
    icon: MessageCircle
  },

  // Analytics
  {
    id: 'analytics-dashboard-guide',
    title: 'Analytics Dashboard Guide',
    description: 'Understanding your performance metrics and insights',
    category: 'analytics',
    type: 'article',
    difficulty: 'beginner',
    readTime: '8 min',
    popularity: 81,
    lastUpdated: '2024-01-07',
    tags: ['analytics', 'metrics', 'dashboard', 'insights'],
    icon: BarChart3
  },
  {
    id: 'content-attribution',
    title: 'Content-to-Lead Attribution',
    description: 'Track which content generates the most leads',
    category: 'analytics',
    type: 'article',
    difficulty: 'intermediate',
    readTime: '9 min',
    popularity: 75,
    lastUpdated: '2024-01-06',
    tags: ['attribution', 'tracking', 'roi', 'content-performance'],
    icon: TrendingUp
  },

  // Settings & Configuration
  {
    id: 'profile-optimization',
    title: 'Profile Optimization Guide',
    description: 'Optimize your profile for better content personalization',
    category: 'settings',
    type: 'guide',
    difficulty: 'beginner',
    readTime: '6 min',
    popularity: 83,
    lastUpdated: '2024-01-05',
    tags: ['profile', 'optimization', 'personalization'],
    icon: Settings
  },
  {
    id: 'integrations-setup',
    title: 'LinkedIn Integration Setup',
    description: 'Connect your LinkedIn account for automated posting',
    category: 'settings',
    type: 'article',
    difficulty: 'beginner',
    readTime: '5 min',
    popularity: 78,
    lastUpdated: '2024-01-04',
    tags: ['integration', 'linkedin', 'setup', 'automation'],
    icon: Heart
  },

  // Troubleshooting
  {
    id: 'common-issues',
    title: 'Common Issues & Solutions',
    description: 'Quick fixes for frequently encountered problems',
    category: 'troubleshooting',
    type: 'faq',
    difficulty: 'beginner',
    readTime: '4 min',
    popularity: 72,
    lastUpdated: '2024-01-03',
    tags: ['troubleshooting', 'issues', 'solutions', 'faq'],
    icon: HelpCircle
  },
  {
    id: 'performance-optimization',
    title: 'Performance Optimization',
    description: 'Speed up the platform and improve your experience',
    category: 'troubleshooting',
    type: 'article',
    difficulty: 'advanced',
    readTime: '11 min',
    popularity: 68,
    lastUpdated: '2024-01-02',
    tags: ['performance', 'optimization', 'speed', 'experience'],
    icon: Shield
  }
]

const categories = {
  'getting-started': { label: 'Getting Started', icon: Rocket, color: 'bg-blue-500' },
  'content-creation': { label: 'Content Creation', icon: FileText, color: 'bg-green-500' },
  'lead-management': { label: 'Lead Management', icon: Users, color: 'bg-purple-500' },
  'analytics': { label: 'Analytics', icon: BarChart3, color: 'bg-orange-500' },
  'settings': { label: 'Settings', icon: Settings, color: 'bg-gray-500' },
  'troubleshooting': { label: 'Troubleshooting', icon: HelpCircle, color: 'bg-red-500' }
}

const typeIcons = {
  article: FileText,
  video: Video,
  faq: HelpCircle,
  guide: Book
}

const difficultyColors = {
  beginner: 'text-green-600 bg-green-100',
  intermediate: 'text-yellow-600 bg-yellow-100',
  advanced: 'text-red-600 bg-red-100'
}

export function HelpCenter({ 
  className, 
  initialSearchQuery = '',
  showCategories = true
}: HelpCenterProps) {
  const [searchQuery, setSearchQuery] = useState(initialSearchQuery)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [selectedArticle, setSelectedArticle] = useState<HelpArticle | null>(null)

  // Search and filter logic
  const filteredArticles = useMemo(() => {
    let filtered = helpArticles

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(article => article.category === selectedCategory)
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(article =>
        article.title.toLowerCase().includes(query) ||
        article.description.toLowerCase().includes(query) ||
        article.tags.some(tag => tag.toLowerCase().includes(query))
      )
    }

    // Sort by popularity
    return filtered.sort((a, b) => b.popularity - a.popularity)
  }, [searchQuery, selectedCategory])

  // Popular articles
  const popularArticles = useMemo(() => {
    return helpArticles
      .sort((a, b) => b.popularity - a.popularity)
      .slice(0, 5)
  }, [])

  return (
    <div className={cn("w-full max-w-6xl mx-auto", className)}>
      {selectedArticle ? (
        // Article View
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              onClick={() => setSelectedArticle(null)}
              className="mb-4"
            >
              ← Back to Help Center
            </Button>
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <Badge variant="outline" className={difficultyColors[selectedArticle.difficulty]}>
                      {selectedArticle.difficulty}
                    </Badge>
                    <Badge variant="outline">
                      {selectedArticle.readTime}
                    </Badge>
                    <Badge variant="outline">
                      {selectedArticle.category.replace('-', ' ')}
                    </Badge>
                  </div>
                  <CardTitle className="text-2xl">{selectedArticle.title}</CardTitle>
                  <p className="text-gray-600 mt-2">{selectedArticle.description}</p>
                </div>
                <div className="text-right">
                  <div className="flex items-center space-x-1 text-yellow-500 mb-1">
                    <Star className="w-4 h-4 fill-current" />
                    <span className="text-sm">{selectedArticle.popularity}%</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    Updated {new Date(selectedArticle.lastUpdated).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {selectedArticle.content ? (
                <div className="prose max-w-none">
                  <div dangerouslySetInnerHTML={{ 
                    __html: selectedArticle.content.replace(/\n/g, '<br>') 
                  }} />
                </div>
              ) : (
                <div className="text-center py-12">
                  <Book className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-700 mb-2">Article Content</h3>
                  <p className="text-gray-500">
                    This article's full content would be displayed here in the actual implementation.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        // Help Center Overview
        <div className="space-y-6">
          {/* Header */}
          <Card>
            <CardHeader>
              <div className="text-center">
                <CardTitle className="text-3xl mb-2">Help Center</CardTitle>
                <p className="text-gray-600 mb-6">
                  Find answers, learn best practices, and get the most out of your technical leadership platform
                </p>
                
                {/* Search */}
                <div className="max-w-md mx-auto relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <Input
                    placeholder="Search help articles..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
            </CardHeader>
          </Card>

          <div className="grid lg:grid-cols-4 gap-6">
            {/* Sidebar */}
            <div className="lg:col-span-1">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Categories</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Button
                    variant={selectedCategory === 'all' ? 'default' : 'ghost'}
                    className="w-full justify-start"
                    onClick={() => setSelectedCategory('all')}
                  >
                    <Book className="w-4 h-4 mr-2" />
                    All Articles
                    <span className="ml-auto text-xs">
                      {helpArticles.length}
                    </span>
                  </Button>
                  
                  {Object.entries(categories).map(([key, category]) => {
                    const Icon = category.icon
                    const count = helpArticles.filter(a => a.category === key).length
                    
                    return (
                      <Button
                        key={key}
                        variant={selectedCategory === key ? 'default' : 'ghost'}
                        className="w-full justify-start"
                        onClick={() => setSelectedCategory(key)}
                      >
                        <Icon className="w-4 h-4 mr-2" />
                        {category.label}
                        <span className="ml-auto text-xs">{count}</span>
                      </Button>
                    )
                  })}
                </CardContent>
              </Card>

              {/* Popular Articles */}
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <Star className="w-4 h-4 mr-2 text-yellow-500" />
                    Popular
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {popularArticles.map((article) => (
                    <button
                      key={article.id}
                      onClick={() => setSelectedArticle(article)}
                      className="w-full text-left p-2 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="font-medium text-sm mb-1">{article.title}</div>
                      <div className="text-xs text-gray-500">{article.readTime}</div>
                    </button>
                  ))}
                </CardContent>
              </Card>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3">
              <div className="space-y-4">
                {/* Results Summary */}
                {(searchQuery || selectedCategory !== 'all') && (
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-600">
                      {filteredArticles.length} article{filteredArticles.length !== 1 ? 's' : ''} found
                      {searchQuery && ` for "${searchQuery}"`}
                      {selectedCategory !== 'all' && ` in ${categories[selectedCategory as keyof typeof categories]?.label}`}
                    </p>
                    {(searchQuery || selectedCategory !== 'all') && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSearchQuery('')
                          setSelectedCategory('all')
                        }}
                      >
                        Clear filters
                      </Button>
                    )}
                  </div>
                )}

                {/* Articles Grid */}
                <div className="space-y-4">
                  {filteredArticles.map((article) => {
                    const Icon = article.icon || typeIcons[article.type]
                    const categoryInfo = categories[article.category]
                    
                    return (
                      <Card
                        key={article.id}
                        className="hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => setSelectedArticle(article)}
                      >
                        <CardContent className="p-6">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2 mb-2">
                                <div className={cn(
                                  "w-8 h-8 rounded-full flex items-center justify-center",
                                  categoryInfo.color
                                )}>
                                  <Icon className="w-4 h-4 text-white" />
                                </div>
                                <Badge variant="outline" className={difficultyColors[article.difficulty]}>
                                  {article.difficulty}
                                </Badge>
                                <Badge variant="outline">
                                  {article.type}
                                </Badge>
                              </div>
                              
                              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                                {article.title}
                              </h3>
                              <p className="text-gray-600 mb-3 leading-relaxed">
                                {article.description}
                              </p>
                              
                              <div className="flex items-center space-x-4 text-sm text-gray-500">
                                <div className="flex items-center space-x-1">
                                  <Clock className="w-3 h-3" />
                                  <span>{article.readTime}</span>
                                </div>
                                <div className="flex items-center space-x-1">
                                  <Star className="w-3 h-3 text-yellow-500 fill-current" />
                                  <span>{article.popularity}%</span>
                                </div>
                                <div>
                                  {categoryInfo.label}
                                </div>
                              </div>
                              
                              {/* Tags */}
                              <div className="flex flex-wrap gap-1 mt-3">
                                {article.tags.slice(0, 3).map((tag) => (
                                  <Badge key={tag} variant="secondary" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                                {article.tags.length > 3 && (
                                  <Badge variant="secondary" className="text-xs">
                                    +{article.tags.length - 3}
                                  </Badge>
                                )}
                              </div>
                            </div>
                            
                            <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0 ml-4" />
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>

                {/* No Results */}
                {filteredArticles.length === 0 && (
                  <Card>
                    <CardContent className="text-center py-12">
                      <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-700 mb-2">No articles found</h3>
                      <p className="text-gray-500 mb-4">
                        Try adjusting your search query or browse by category.
                      </p>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setSearchQuery('')
                          setSelectedCategory('all')
                        }}
                      >
                        Browse All Articles
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}