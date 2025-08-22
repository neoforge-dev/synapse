"use client"

import React, { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  ChevronDown,
  ChevronRight,
  Search,
  HelpCircle,
  Zap,
  FileText,
  Users,
  Settings,
  Shield,
  CreditCard
} from 'lucide-react'

interface FAQItem {
  id: string
  question: string
  answer: string
  category: 'general' | 'content' | 'leads' | 'billing' | 'technical' | 'security'
  tags: string[]
  popularity: number
}

interface FAQSectionProps {
  className?: string
  showSearch?: boolean
  maxItems?: number
}

const faqItems: FAQItem[] = [
  // General
  {
    id: 'what-is-platform',
    question: 'What is TechLead AutoPilot?',
    answer: 'TechLead AutoPilot is a comprehensive platform that helps technical leaders systematically build their professional brand and generate consultation opportunities through automated content creation and intelligent lead detection.',
    category: 'general',
    tags: ['platform', 'overview', 'features'],
    popularity: 95
  },
  {
    id: 'how-it-works',
    question: 'How does the platform work?',
    answer: 'The platform works in three main steps: 1) Generate high-quality technical content using AI, 2) Automatically detect consultation opportunities from engagement, and 3) Track and manage leads to convert them into clients. Everything is designed to work systematically with minimal manual effort.',
    category: 'general',
    tags: ['workflow', 'process', 'automation'],
    popularity: 89
  },
  {
    id: 'getting-started-time',
    question: 'How long does it take to get started?',
    answer: 'You can be up and running in about 5-10 minutes. Complete your profile, take the product tour, and generate your first piece of content. The platform is designed for immediate value with progressive depth.',
    category: 'general',
    tags: ['onboarding', 'setup', 'time'],
    popularity: 87
  },

  // Content Creation
  {
    id: 'content-quality',
    question: 'How good is the AI-generated content?',
    answer: 'Our AI generates high-quality, personalized content based on your expertise and industry. The content is designed to establish thought leadership and attract ideal consulting clients. You can always edit and refine before publishing.',
    category: 'content',
    tags: ['ai', 'quality', 'personalization'],
    popularity: 91
  },
  {
    id: 'content-customization',
    question: 'Can I customize the generated content?',
    answer: 'Absolutely! All generated content can be edited, refined, or completely rewritten. The platform provides a strong starting point that you can customize to match your voice and specific messaging needs.',
    category: 'content',
    tags: ['customization', 'editing', 'personalization'],
    popularity: 84
  },
  {
    id: 'posting-frequency',
    question: 'How often should I post content?',
    answer: 'We recommend posting 2-3 times per week for optimal engagement. The platform suggests optimal posting times (Tuesday/Thursday 6:30 AM) based on engagement data for technical leadership content.',
    category: 'content',
    tags: ['frequency', 'scheduling', 'best-practices'],
    popularity: 78
  },
  {
    id: 'content-types',
    question: 'What types of content can I create?',
    answer: 'You can create various content types including thought leadership posts, technical insights, case studies, career advice, industry commentary, team building tips, and more. Each template is optimized for different engagement goals.',
    category: 'content',
    tags: ['templates', 'types', 'variety'],
    popularity: 82
  },

  // Lead Management
  {
    id: 'lead-detection-accuracy',
    question: 'How accurate is the lead detection?',
    answer: 'Our AI achieves 85-92% accuracy in identifying genuine consultation opportunities. It analyzes engagement patterns, comment sentiment, and specific language indicators to score leads from 1-10.',
    category: 'leads',
    tags: ['accuracy', 'ai', 'scoring'],
    popularity: 88
  },
  {
    id: 'lead-types',
    question: 'What types of leads does the platform detect?',
    answer: 'The platform identifies various consultation opportunities including technical architecture reviews, team scaling advice, leadership coaching, process optimization, and strategic technical consulting.',
    category: 'leads',
    tags: ['types', 'opportunities', 'consulting'],
    popularity: 79
  },
  {
    id: 'false-positives',
    question: 'What about false positive leads?',
    answer: 'The system includes confidence scoring to minimize false positives. Leads with scores below 6 are marked as low confidence, and you can provide feedback to improve accuracy over time.',
    category: 'leads',
    tags: ['false-positives', 'accuracy', 'feedback'],
    popularity: 71
  },

  // Technical
  {
    id: 'integrations',
    question: 'What integrations are available?',
    answer: 'Currently, we support LinkedIn integration for automated posting and engagement tracking. Additional integrations (Twitter, newsletter platforms, CRM systems) are in development.',
    category: 'technical',
    tags: ['integrations', 'linkedin', 'api'],
    popularity: 75
  },
  {
    id: 'data-export',
    question: 'Can I export my data?',
    answer: 'Yes, you can export all your data including content, leads, analytics, and settings. We support CSV, JSON, and PDF formats depending on the data type.',
    category: 'technical',
    tags: ['export', 'data', 'portability'],
    popularity: 68
  },
  {
    id: 'mobile-app',
    question: 'Is there a mobile app?',
    answer: 'The platform is a Progressive Web App (PWA) that works seamlessly on mobile devices. You can install it on your phone for native app-like experience without needing separate downloads.',
    category: 'technical',
    tags: ['mobile', 'pwa', 'app'],
    popularity: 73
  },

  // Security
  {
    id: 'data-privacy',
    question: 'How is my data protected?',
    answer: 'We use enterprise-grade security including encrypted data storage, secure API communications, and strict access controls. Your content and leads data is never shared with third parties.',
    category: 'security',
    tags: ['privacy', 'security', 'encryption'],
    popularity: 86
  },
  {
    id: 'linkedin-permissions',
    question: 'What LinkedIn permissions do you need?',
    answer: 'We only request minimal permissions needed for posting content and reading engagement metrics. We cannot access your private messages, connections, or personal information.',
    category: 'security',
    tags: ['permissions', 'linkedin', 'oauth'],
    popularity: 77
  },

  // Billing
  {
    id: 'pricing-model',
    question: 'What is the pricing model?',
    answer: 'We offer subscription-based pricing with different tiers based on usage. All plans include core features with higher tiers offering additional integrations, advanced analytics, and priority support.',
    category: 'billing',
    tags: ['pricing', 'subscription', 'tiers'],
    popularity: 83
  },
  {
    id: 'free-trial',
    question: 'Is there a free trial?',
    answer: 'Yes, we offer a 14-day free trial with full access to all features. No credit card required to start, and you can upgrade or cancel anytime during or after the trial.',
    category: 'billing',
    tags: ['trial', 'free', 'credit-card'],
    popularity: 90
  }
]

const categories = {
  general: { label: 'General', icon: HelpCircle, color: 'bg-blue-500' },
  content: { label: 'Content Creation', icon: FileText, color: 'bg-green-500' },
  leads: { label: 'Lead Management', icon: Users, color: 'bg-purple-500' },
  technical: { label: 'Technical', icon: Zap, color: 'bg-orange-500' },
  security: { label: 'Security & Privacy', icon: Shield, color: 'bg-red-500' },
  billing: { label: 'Billing & Plans', icon: CreditCard, color: 'bg-gray-500' }
}

export function FAQSection({ className, showSearch = true, maxItems }: FAQSectionProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedItems(newExpanded)
  }

  const filteredFAQs = faqItems
    .filter(item => {
      if (selectedCategory !== 'all' && item.category !== selectedCategory) return false
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          item.question.toLowerCase().includes(query) ||
          item.answer.toLowerCase().includes(query) ||
          item.tags.some(tag => tag.toLowerCase().includes(query))
        )
      }
      return true
    })
    .sort((a, b) => b.popularity - a.popularity)
    .slice(0, maxItems)

  return (
    <div className={cn("w-full", className)}>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Frequently Asked Questions</h2>
        <p className="text-gray-600">Find quick answers to common questions</p>
      </div>

      {showSearch && (
        <div className="mb-6 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <Input
              placeholder="Search FAQs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Category Filters */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={selectedCategory === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory('all')}
            >
              All Questions
              <Badge variant="secondary" className="ml-2">
                {faqItems.length}
              </Badge>
            </Button>
            
            {Object.entries(categories).map(([key, category]) => {
              const Icon = category.icon
              const count = faqItems.filter(item => item.category === key).length
              
              return (
                <Button
                  key={key}
                  variant={selectedCategory === key ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedCategory(key)}
                  className="flex items-center space-x-1"
                >
                  <Icon className="w-3 h-3" />
                  <span>{category.label}</span>
                  <Badge variant="secondary" className="ml-1">
                    {count}
                  </Badge>
                </Button>
              )
            })}
          </div>
        </div>
      )}

      {/* FAQ Items */}
      <div className="space-y-3">
        {filteredFAQs.map((item) => {
          const isExpanded = expandedItems.has(item.id)
          const categoryInfo = categories[item.category]
          
          return (
            <Card key={item.id} className="overflow-hidden">
              <button
                onClick={() => toggleExpanded(item.id)}
                className="w-full p-4 text-left hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 pr-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className={cn(
                        "w-6 h-6 rounded-full flex items-center justify-center",
                        categoryInfo.color
                      )}>
                        <categoryInfo.icon className="w-3 h-3 text-white" />
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {categoryInfo.label}
                      </Badge>
                      {item.popularity >= 85 && (
                        <Badge variant="secondary" className="text-xs">
                          Popular
                        </Badge>
                      )}
                    </div>
                    <h3 className="font-medium text-gray-900 leading-relaxed">
                      {item.question}
                    </h3>
                  </div>
                  <div className="flex-shrink-0">
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                </div>
              </button>
              
              {isExpanded && (
                <CardContent className="pt-0 px-4 pb-4">
                  <div className="pl-8">
                    <p className="text-gray-600 leading-relaxed mb-3">
                      {item.answer}
                    </p>
                    
                    {/* Tags */}
                    <div className="flex flex-wrap gap-1">
                      {item.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          )
        })}
      </div>

      {/* No Results */}
      {filteredFAQs.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <HelpCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">No FAQs found</h3>
            <p className="text-gray-500 mb-4">
              Try adjusting your search query or browse by category.
            </p>
            <div className="flex items-center justify-center space-x-3">
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery('')
                  setSelectedCategory('all')
                }}
              >
                Clear Filters
              </Button>
              <Button onClick={() => window.open('/help', '_blank')}>
                Browse Help Center
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Show More Link */}
      {maxItems && filteredFAQs.length === maxItems && (
        <div className="text-center mt-6">
          <Button variant="outline" onClick={() => window.open('/help', '_blank')}>
            View All FAQs in Help Center
          </Button>
        </div>
      )}
    </div>
  )
}