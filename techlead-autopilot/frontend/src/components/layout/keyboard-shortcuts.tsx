"use client"

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { 
  Command, 
  Search, 
  LayoutDashboard, 
  FileText, 
  Users, 
  BarChart3, 
  Settings,
  Plus,
  RefreshCw,
  HelpCircle,
  ChevronLeft,
  Home
} from 'lucide-react'

interface KeyboardShortcut {
  category: string
  shortcuts: {
    keys: string[]
    description: string
    action?: () => void
  }[]
}

interface KeyboardShortcutsProps {
  onOpenSearch?: () => void
  onToggleSidebar?: () => void
}

export function KeyboardShortcuts({ onOpenSearch, onToggleSidebar }: KeyboardShortcutsProps) {
  const [isHelpOpen, setIsHelpOpen] = useState(false)
  const router = useRouter()

  const shortcuts: KeyboardShortcut[] = [
    {
      category: "Navigation",
      shortcuts: [
        {
          keys: ["⌘", "K"],
          description: "Open universal search",
          action: onOpenSearch
        },
        {
          keys: ["⌘", "B"],
          description: "Toggle sidebar",
          action: onToggleSidebar
        },
        {
          keys: ["⌘", "H"],
          description: "Go to dashboard",
          action: () => router.push('/dashboard')
        },
        {
          keys: ["⌘", "1"],
          description: "Go to content library",
          action: () => router.push('/dashboard/content')
        },
        {
          keys: ["⌘", "2"],
          description: "Go to leads",
          action: () => router.push('/dashboard/leads')
        },
        {
          keys: ["⌘", "3"],
          description: "Go to analytics",
          action: () => router.push('/dashboard/content/analytics')
        },
        {
          keys: ["⌘", ","],
          description: "Open settings",
          action: () => router.push('/dashboard/settings')
        }
      ]
    },
    {
      category: "Quick Actions",
      shortcuts: [
        {
          keys: ["⌘", "N"],
          description: "Generate new content",
          action: () => router.push('/dashboard/content/generate')
        },
        {
          keys: ["⌘", "Shift", "L"],
          description: "View high priority leads",
          action: () => router.push('/dashboard/leads?priority=high')
        },
        {
          keys: ["⌘", "R"],
          description: "Refresh current page",
          action: () => window.location.reload()
        },
        {
          keys: ["⌘", "Enter"],
          description: "Quick approve (context dependent)"
        }
      ]
    },
    {
      category: "Help & Support",
      shortcuts: [
        {
          keys: ["⌘", "?"],
          description: "Show keyboard shortcuts",
          action: () => setIsHelpOpen(true)
        },
        {
          keys: ["⌘", "Shift", "H"],
          description: "Open help center",
          action: () => router.push('/dashboard/help')
        }
      ]
    },
    {
      category: "General",
      shortcuts: [
        {
          keys: ["Esc"],
          description: "Close modals/dialogs"
        },
        {
          keys: ["↑", "↓"],
          description: "Navigate lists"
        },
        {
          keys: ["Enter"],
          description: "Select/confirm"
        },
        {
          keys: ["Tab"],
          description: "Navigate form fields"
        }
      ]
    }
  ]

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check for modifier key combinations
      if (e.metaKey || e.ctrlKey) {
        switch (e.key.toLowerCase()) {
          case 'k':
            e.preventDefault()
            onOpenSearch?.()
            break
          case 'b':
            e.preventDefault()
            onToggleSidebar?.()
            break
          case 'h':
            if (!e.shiftKey) {
              e.preventDefault()
              router.push('/dashboard')
            } else {
              e.preventDefault()
              router.push('/dashboard/help')
            }
            break
          case '1':
            e.preventDefault()
            router.push('/dashboard/content')
            break
          case '2':
            e.preventDefault()
            router.push('/dashboard/leads')
            break
          case '3':
            e.preventDefault()
            router.push('/dashboard/content/analytics')
            break
          case ',':
            e.preventDefault()
            router.push('/dashboard/settings')
            break
          case 'n':
            e.preventDefault()
            router.push('/dashboard/content/generate')
            break
          case 'l':
            if (e.shiftKey) {
              e.preventDefault()
              router.push('/dashboard/leads?priority=high')
            }
            break
          case 'r':
            e.preventDefault()
            window.location.reload()
            break
          case '/':
          case '?':
            e.preventDefault()
            setIsHelpOpen(true)
            break
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [router, onOpenSearch, onToggleSidebar])

  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0

  const formatKey = (key: string) => {
    if (key === '⌘' && !isMac) return 'Ctrl'
    return key
  }

  return (
    <Dialog open={isHelpOpen} onOpenChange={setIsHelpOpen}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Command className="w-5 h-5" />
            <span>Keyboard Shortcuts</span>
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          {shortcuts.map((category) => (
            <div key={category.category}>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                {category.category}
              </h3>
              <div className="space-y-2">
                {category.shortcuts.map((shortcut, index) => (
                  <div 
                    key={index}
                    className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <span className="text-sm text-gray-700">
                      {shortcut.description}
                    </span>
                    <div className="flex items-center space-x-1">
                      {shortcut.keys.map((key, keyIndex) => (
                        <React.Fragment key={keyIndex}>
                          <Badge variant="outline" className="text-xs font-mono px-2 py-1">
                            {formatKey(key)}
                          </Badge>
                          {keyIndex < shortcut.keys.length - 1 && (
                            <span className="text-gray-400 text-xs">+</span>
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <HelpCircle className="w-4 h-4 text-blue-600" />
              </div>
            </div>
            <div>
              <h4 className="text-sm font-medium text-blue-900 mb-1">
                Pro Tips
              </h4>
              <ul className="text-xs text-blue-700 space-y-1">
                <li>• Most shortcuts work from anywhere in the app</li>
                <li>• Use Tab to navigate through forms and buttons</li>
                <li>• Arrow keys work in lists and search results</li>
                <li>• Press Escape to close any modal or dropdown</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="flex justify-center pt-4">
          <button
            onClick={() => setIsHelpOpen(false)}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Press Escape to close
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// Hook for using keyboard shortcuts in other components
export function useKeyboardShortcuts(actions: {
  onOpenSearch?: () => void
  onToggleSidebar?: () => void
  onQuickApprove?: () => void
  customShortcuts?: Record<string, () => void>
} = {}) {
  const router = useRouter()

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Handle custom shortcuts first
      if (actions.customShortcuts) {
        const key = `${e.metaKey || e.ctrlKey ? 'cmd+' : ''}${e.shiftKey ? 'shift+' : ''}${e.key.toLowerCase()}`
        if (actions.customShortcuts[key]) {
          e.preventDefault()
          actions.customShortcuts[key]()
          return
        }
      }

      // Quick approve with Cmd+Enter
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && actions.onQuickApprove) {
        e.preventDefault()
        actions.onQuickApprove()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [actions, router])
}