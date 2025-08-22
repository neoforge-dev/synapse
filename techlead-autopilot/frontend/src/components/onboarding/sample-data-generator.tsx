"use client"

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  Database,
  FileText,
  Users,
  BarChart3,
  CheckCircle,
  Loader2,
  Sparkles,
  Lightbulb,
  TrendingUp,
  Target,
  Calendar,
  MessageSquare
} from 'lucide-react'

interface SampleDataSet {
  id: string
  name: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  itemCount: number
  category: 'content' | 'leads' | 'analytics'
  estimatedTime: string
  data: any[]
}

interface SampleDataGeneratorProps {
  onDataGenerated?: (dataSet: SampleDataSet) => void
  onAllGenerated?: () => void
  className?: string
}

const sampleDataSets: SampleDataSet[] = [
  {
    id: 'sample-content',
    name: 'Sample Content Library',
    description: 'Pre-generated LinkedIn posts showcasing different content types and topics',
    icon: FileText,
    itemCount: 8,
    category: 'content',
    estimatedTime: '2 sec',
    data: [
      {
        id: 'content-1',
        title: 'Engineering Leadership Best Practices',
        content: '# Engineering Leadership in 2024\n\nLeading engineering teams requires a unique blend of technical expertise and people skills. Here are the key practices I\'ve learned:\n\n1. **Clear Communication** - Technical decisions must be communicated clearly to both technical and non-technical stakeholders.\n\n2. **Continuous Learning** - Technology evolves rapidly. Great leaders stay current while helping their teams grow.\n\n3. **Empathy in Code Reviews** - Code reviews are teaching moments, not critique sessions.\n\nWhat leadership practices have worked best for your team?\n\n#TechnicalLeadership #EngineeringManagement #TeamGrowth',
        contentType: 'linkedin_post',
        status: 'published',
        createdAt: '2024-01-15T10:00:00Z',
        metrics: { views: 2500, likes: 125, comments: 18, shares: 12 }
      },
      {
        id: 'content-2',
        title: 'Scaling Engineering Teams Effectively',
        content: '🚀 **Scaling Engineering Teams: Lessons from the Trenches**\n\nAfter growing engineering teams from 5 to 50+ engineers, here\'s what I wish I knew earlier:\n\n• **Hire for potential, not just experience** - Look for growth mindset and learning ability\n• **Build systems, not dependencies** - Create processes that work without constant oversight\n• **Maintain code quality** - Technical debt compounds faster than you think\n• **Foster ownership** - Give engineers autonomy and accountability\n\nThe hardest part isn\'t hiring fast enough—it\'s maintaining culture and quality while growing.\n\n#EngineeringLeadership #Scaling #TechManagement',
        contentType: 'linkedin_post',
        status: 'published',
        createdAt: '2024-01-12T14:30:00Z',
        metrics: { views: 3200, likes: 200, comments: 35, shares: 28 }
      },
      {
        id: 'content-3',
        title: 'Remote Team Management Strategies',
        content: '🏠 **Remote Engineering Teams: Making It Work**\n\nThree years of remote-first engineering management taught me:\n\n1. **Over-communicate by default** - What feels like too much is probably just right\n2. **Async > meetings** - Respect different time zones and work styles\n3. **Document everything** - If it\'s not written down, it doesn\'t exist\n4. **Intentional culture building** - Remote culture requires deliberate effort\n\nRemote work isn\'t about replicating the office online—it\'s about building something better.\n\n#RemoteWork #EngineeringManagement #DistributedTeams',
        contentType: 'linkedin_post',
        status: 'draft',
        createdAt: '2024-01-10T09:15:00Z',
        metrics: { views: 0, likes: 0, comments: 0, shares: 0 }
      }
    ]
  },
  {
    id: 'sample-leads',
    name: 'Sample Lead Pipeline',
    description: 'Demo consultation opportunities detected from content engagement',
    icon: Users,
    itemCount: 12,
    category: 'leads',
    estimatedTime: '1 sec',
    data: [
      {
        id: 'lead-1',
        name: 'Sarah Chen',
        title: 'VP Engineering',
        company: 'TechFlow Inc',
        email: 'sarah.chen@techflow.com',
        linkedinProfile: 'https://linkedin.com/in/sarahchen',
        content: 'Great insights on scaling engineering teams! We\'re facing similar challenges at TechFlow. Would love to discuss potential consulting opportunities.',
        sourcePost: 'content-2',
        leadScore: 9,
        priority: 'high',
        status: 'new',
        estimatedValue: 15000,
        confidence: 0.92,
        detectedAt: '2024-01-16T11:30:00Z',
        tags: ['consultation', 'scaling', 'high-value']
      },
      {
        id: 'lead-2',
        name: 'Michael Rodriguez',
        title: 'CTO',
        company: 'StartupCo',
        email: 'mike@startupco.io',
        linkedinProfile: 'https://linkedin.com/in/mikerodriguez',
        content: 'Your post about remote team management resonates deeply. We\'re struggling with similar issues as we grow. Any chance we could chat?',
        sourcePost: 'content-3',
        leadScore: 8,
        priority: 'high',
        status: 'contacted',
        estimatedValue: 8000,
        confidence: 0.85,
        detectedAt: '2024-01-14T16:45:00Z',
        tags: ['consultation', 'remote-work', 'startup']
      },
      {
        id: 'lead-3',
        name: 'Emily Zhang',
        title: 'Engineering Manager',
        company: 'DataCorp',
        email: 'emily.zhang@datacorp.com',
        linkedinProfile: 'https://linkedin.com/in/emilyzhang',
        content: 'Thanks for sharing this! We\'re implementing similar practices at DataCorp. Would be interested in learning more about your consulting services.',
        sourcePost: 'content-1',
        leadScore: 7,
        priority: 'medium',
        status: 'qualified',
        estimatedValue: 5000,
        confidence: 0.78,
        detectedAt: '2024-01-13T08:20:00Z',
        tags: ['consultation', 'management', 'medium-value']
      }
    ]
  },
  {
    id: 'sample-analytics',
    name: 'Sample Analytics Data',
    description: 'Performance metrics and insights to demonstrate platform capabilities',
    icon: BarChart3,
    itemCount: 6,
    category: 'analytics',
    estimatedTime: '1 sec',
    data: [
      {
        id: 'analytics-overview',
        timeframe: '30 days',
        metrics: {
          totalContent: 15,
          totalViews: 45000,
          totalEngagement: 2250,
          averageEngagementRate: 5.2,
          totalLeads: 28,
          qualifiedLeads: 12,
          conversionRate: 42.8,
          estimatedPipelineValue: 180000
        }
      },
      {
        id: 'content-performance',
        topPerformingContent: [
          { id: 'content-2', title: 'Scaling Engineering Teams', views: 3200, engagement: 263 },
          { id: 'content-1', title: 'Engineering Leadership', views: 2500, engagement: 155 },
          { id: 'content-3', title: 'Remote Team Management', views: 1800, engagement: 142 }
        ]
      },
      {
        id: 'lead-sources',
        leadsBySource: [
          { source: 'LinkedIn Posts', count: 18, value: 120000 },
          { source: 'Article Comments', count: 7, value: 45000 },
          { source: 'Direct Messages', count: 3, value: 15000 }
        ]
      }
    ]
  }
]

export function SampleDataGenerator({ onDataGenerated, onAllGenerated, className }: SampleDataGeneratorProps) {
  const [generatingSet, setGeneratingSet] = useState<string | null>(null)
  const [generatedSets, setGeneratedSets] = useState<Set<string>>(new Set())
  const [progress, setProgress] = useState(0)

  const generateSampleData = async (dataSet: SampleDataSet) => {
    setGeneratingSet(dataSet.id)
    setProgress(0)

    // Simulate progressive generation
    for (let i = 0; i <= 100; i += 10) {
      await new Promise(resolve => setTimeout(resolve, 50))
      setProgress(i)
    }

    // Mark as generated
    const newGenerated = new Set(generatedSets)
    newGenerated.add(dataSet.id)
    setGeneratedSets(newGenerated)
    setGeneratingSet(null)
    setProgress(0)

    // Store in localStorage for persistence
    localStorage.setItem(`sample-data-${dataSet.id}`, JSON.stringify(dataSet.data))
    localStorage.setItem('sample-data-generated', JSON.stringify([...newGenerated]))

    onDataGenerated?.(dataSet)

    // Check if all sets are generated
    if (newGenerated.size === sampleDataSets.length) {
      onAllGenerated?.()
    }
  }

  const generateAllData = async () => {
    for (const dataSet of sampleDataSets) {
      if (!generatedSets.has(dataSet.id)) {
        await generateSampleData(dataSet)
        await new Promise(resolve => setTimeout(resolve, 200))
      }
    }
  }

  const isGenerated = (setId: string) => generatedSets.has(setId)
  const isGenerating = (setId: string) => generatingSet === setId
  const allGenerated = generatedSets.size === sampleDataSets.length

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-blue-500" />
              <span>Sample Data Generator</span>
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              Generate sample data to explore platform features immediately
            </p>
          </div>
          <Button
            onClick={generateAllData}
            disabled={allGenerated || generatingSet !== null}
            className="flex items-center space-x-2"
          >
            {allGenerated ? (
              <CheckCircle className="w-4 h-4" />
            ) : generatingSet ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>
              {allGenerated ? 'All Generated' : generatingSet ? 'Generating...' : 'Generate All'}
            </span>
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {sampleDataSets.map((dataSet) => {
          const Icon = dataSet.icon
          const generated = isGenerated(dataSet.id)
          const generating = isGenerating(dataSet.id)

          return (
            <div
              key={dataSet.id}
              className={cn(
                "p-4 border rounded-lg transition-all",
                generated ? "bg-green-50 border-green-200" : "border-gray-200 hover:border-gray-300"
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <div className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center",
                    generated ? "bg-green-100" : "bg-gray-100"
                  )}>
                    <Icon className={cn(
                      "w-5 h-5",
                      generated ? "text-green-600" : "text-gray-600"
                    )} />
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className={cn(
                        "font-medium",
                        generated ? "text-green-900" : "text-gray-900"
                      )}>
                        {dataSet.name}
                      </h3>
                      <Badge variant={generated ? 'default' : 'outline'} className="text-xs">
                        {dataSet.itemCount} items
                      </Badge>
                    </div>
                    
                    <p className={cn(
                      "text-sm mb-3",
                      generated ? "text-green-700" : "text-gray-600"
                    )}>
                      {dataSet.description}
                    </p>

                    {generating && (
                      <div className="mb-3">
                        <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                          <span>Generating sample data...</span>
                          <span>{progress}%</span>
                        </div>
                        <Progress value={progress} className="h-1" />
                      </div>
                    )}

                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span className="flex items-center space-x-1">
                        <Target className="w-3 h-3" />
                        <span>{dataSet.category}</span>
                      </span>
                      <span className="flex items-center space-x-1">
                        <Calendar className="w-3 h-3" />
                        <span>{dataSet.estimatedTime}</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex-shrink-0 ml-4">
                  {generated ? (
                    <div className="flex items-center space-x-2 text-green-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="text-sm font-medium">Generated</span>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => generateSampleData(dataSet)}
                      disabled={generating}
                      variant="outline"
                    >
                      {generating ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        'Generate'
                      )}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )
        })}

        {/* Benefits Section */}
        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-start space-x-3">
            <Lightbulb className="w-5 h-5 text-blue-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-blue-900 mb-2">Why Generate Sample Data?</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• <strong>Immediate Value:</strong> See the platform in action with realistic data</li>
                <li>• <strong>Feature Exploration:</strong> Test all features without waiting for real data</li>
                <li>• <strong>Learning Experience:</strong> Understand workflows with practical examples</li>
                <li>• <strong>Demo Ready:</strong> Perfect for showing the platform to stakeholders</li>
              </ul>
            </div>
          </div>
        </div>

        {allGenerated && (
          <div className="mt-4 p-4 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h4 className="font-medium text-green-900">Sample Data Ready! 🎉</h4>
                <p className="text-sm text-green-700">
                  Explore the platform with realistic data. Navigate to Content, Leads, or Analytics to see it in action.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}