"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Search, FileText, Users, BarChart3, Settings, Clock, Hash, ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Dialog, DialogContent } from '@/components/ui/dialog'

interface SearchResult {
  id: string
  title: string
  description: string
  type: 'content' | 'lead' | 'analytics' | 'page' | 'action'
  href: string
  icon: React.ComponentType<{ className?: string }>
  section?: string
  metadata?: string
  score?: number
}

interface UniversalSearchProps {
  isOpen: boolean
  onClose: () => void
}

// Mock search data - in real app this would come from API
const searchData: SearchResult[] = [
  // Pages
  {
    id: 'dashboard',
    title: 'Dashboard',
    description: 'Overview of your technical leadership platform',
    type: 'page',
    href: '/dashboard',
    icon: BarChart3,
    section: 'Navigation'
  },
  {
    id: 'content-library',
    title: 'Content Library',
    description: 'Manage all your generated content',
    type: 'page',
    href: '/dashboard/content',
    icon: FileText,
    section: 'Navigation'
  },
  {
    id: 'lead-management',
    title: 'Lead Management',
    description: 'Track and manage consultation opportunities',
    type: 'page',
    href: '/dashboard/leads',
    icon: Users,
    section: 'Navigation'
  },
  {
    id: 'content-analytics',
    title: 'Content Analytics',
    description: 'Performance metrics and insights',
    type: 'analytics',
    href: '/dashboard/content/analytics',
    icon: BarChart3,
    section: 'Analytics'
  },
  {
    id: 'lead-analytics',
    title: 'Lead Analytics',
    description: 'Lead conversion and pipeline analysis',
    type: 'analytics',
    href: '/dashboard/leads/analytics',
    icon: BarChart3,
    section: 'Analytics'
  },
  {
    id: 'settings',
    title: 'Settings',
    description: 'Configure your account and preferences',
    type: 'page',
    href: '/dashboard/settings',
    icon: Settings,
    section: 'Navigation'
  },
  
  // Actions
  {
    id: 'generate-content',
    title: 'Generate New Content',
    description: 'Create new LinkedIn posts and articles',
    type: 'action',
    href: '/dashboard/content/generate',
    icon: FileText,
    section: 'Quick Actions'
  },
  {
    id: 'view-high-priority-leads',
    title: 'High Priority Leads',
    description: 'View leads with high conversion potential',
    type: 'action',
    href: '/dashboard/leads?priority=high',
    icon: Users,
    section: 'Quick Actions'
  },
  
  // Content examples (would come from API)
  {
    id: 'content-1',
    title: 'Engineering Leadership Best Practices',
    description: 'LinkedIn post about technical leadership principles',
    type: 'content',
    href: '/dashboard/content/1',
    icon: FileText,
    section: 'Recent Content',
    metadata: 'Published 2 days ago'
  },
  {
    id: 'content-2',
    title: 'Scaling Engineering Teams',
    description: 'Article about team growth strategies',
    type: 'content',
    href: '/dashboard/content/2',
    icon: FileText,
    section: 'Recent Content',
    metadata: 'Draft'
  },
  
  // Lead examples (would come from API)
  {
    id: 'lead-1',
    title: 'Sarah Johnson - VP Engineering',
    description: 'High-value consultation opportunity from GrowthTech',
    type: 'lead',
    href: '/dashboard/leads/1',
    icon: Users,
    section: 'Recent Leads',
    metadata: 'Score: 9/10'
  },
  {
    id: 'lead-2',
    title: 'Michael Chen - CTO',
    description: 'Inquiry about engineering team scaling',
    type: 'lead',
    href: '/dashboard/leads/2',
    icon: Users,
    section: 'Recent Leads',
    metadata: 'Score: 7/10'
  }
]

export function UniversalSearch({ isOpen, onClose }: UniversalSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [recentSearches, setRecentSearches] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()

  // Search function
  const performSearch = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) {
      // Show popular/recent items when no query
      setResults(searchData.slice(0, 8))
      return
    }

    const filtered = searchData.filter(item => {
      const searchTerms = searchQuery.toLowerCase().split(' ')
      const searchableText = `${item.title} ${item.description} ${item.section}`.toLowerCase()
      
      return searchTerms.every(term => searchableText.includes(term))
    })

    // Sort by relevance (title matches first, then description)
    const sorted = filtered.sort((a, b) => {
      const aTitle = a.title.toLowerCase().includes(searchQuery.toLowerCase()) ? 1 : 0
      const bTitle = b.title.toLowerCase().includes(searchQuery.toLowerCase()) ? 1 : 0
      return bTitle - aTitle
    })

    setResults(sorted.slice(0, 10))
  }, [])

  // Debounced search
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      performSearch(query)
    }, 150)

    return () => clearTimeout(timeoutId)
  }, [query, performSearch])

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex(prev => Math.min(prev + 1, results.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex(prev => Math.max(prev - 1, 0))
          break
        case 'Enter':
          e.preventDefault()
          if (results[selectedIndex]) {
            handleSelect(results[selectedIndex])
          }
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, results, selectedIndex, onClose])

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Reset state when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      performSearch('')
    }
  }, [isOpen, performSearch])

  const handleSelect = (result: SearchResult) => {
    // Add to recent searches
    setRecentSearches(prev => {
      const updated = [result.title, ...prev.filter(s => s !== result.title)].slice(0, 5)
      return updated
    })

    // Navigate
    router.push(result.href)
    onClose()
  }

  const groupedResults = results.reduce((acc, result) => {
    const section = result.section || 'Other'
    if (!acc[section]) acc[section] = []
    acc[section].push(result)
    return acc
  }, {} as Record<string, SearchResult[]>)

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl p-0 gap-0 overflow-hidden">
        <div className="border-b border-gray-200 p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Search everything... (⌘K)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 text-lg border-0 focus:outline-none focus:ring-0 placeholder-gray-400"
            />
          </div>
        </div>

        <div className="max-h-96 overflow-y-auto">
          {results.length === 0 && query ? (
            <div className="p-8 text-center">
              <Search className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No results found for "{query}"</p>
              <p className="text-sm text-gray-400 mt-1">Try a different search term</p>
            </div>
          ) : (
            <div className="py-2">
              {Object.entries(groupedResults).map(([section, sectionResults]) => (
                <div key={section} className="mb-4">
                  <div className="px-4 py-2">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      {section}
                    </h3>
                  </div>
                  {sectionResults.map((result, index) => {
                    const globalIndex = results.indexOf(result)
                    const Icon = result.icon
                    const isSelected = globalIndex === selectedIndex
                    
                    return (
                      <button
                        key={result.id}
                        onClick={() => handleSelect(result)}
                        className={cn(
                          "w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center space-x-3 transition-colors",
                          isSelected && "bg-blue-50 border-r-2 border-blue-500"
                        )}
                      >
                        <Icon className={cn(
                          "w-5 h-5 flex-shrink-0",
                          isSelected ? "text-blue-600" : "text-gray-400"
                        )} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className={cn(
                              "font-medium truncate",
                              isSelected ? "text-blue-900" : "text-gray-900"
                            )}>
                              {result.title}
                            </p>
                            {result.metadata && (
                              <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                                {result.metadata}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-500 truncate">
                            {result.description}
                          </p>
                        </div>
                        <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center space-x-4">
              <span>↑↓ to navigate</span>
              <span>↵ to select</span>
              <span>esc to close</span>
            </div>
            <div className="flex items-center space-x-1">
              <Hash className="w-3 h-3" />
              <span>Powered by TechLead AutoPilot</span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}