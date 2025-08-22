"use client"

import React, { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { useSession, signOut } from 'next-auth/react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { UniversalSearch } from './universal-search'
import {
  LayoutDashboard,
  FileText,
  Users,
  BarChart3,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Plus,
  Search,
  Bell,
  LogOut,
  User,
  Zap,
  Target,
  TrendingUp,
  Calendar,
  MessageSquare,
  Database
} from 'lucide-react'

interface NavigationItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string | number
  quickActions?: QuickAction[]
}

interface QuickAction {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
}

interface NavigationSection {
  name: string
  items: NavigationItem[]
}

const navigationSections: NavigationSection[] = [
  {
    name: "Overview",
    items: [
      {
        name: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
        quickActions: [
          { name: "View Analytics", href: "/dashboard/analytics", icon: BarChart3 },
          { name: "Generate Content", href: "/dashboard/content/generate", icon: Plus }
        ]
      }
    ]
  },
  {
    name: "Content Management",
    items: [
      {
        name: "Content Library",
        href: "/dashboard/content",
        icon: FileText,
        badge: "12",
        quickActions: [
          { name: "Generate New", href: "/dashboard/content/generate", icon: Plus },
          { name: "View Drafts", href: "/dashboard/content?status=draft", icon: FileText },
          { name: "Scheduled Posts", href: "/dashboard/content?status=scheduled", icon: Calendar }
        ]
      },
      {
        name: "Content Analytics",
        href: "/dashboard/content/analytics",
        icon: TrendingUp,
        quickActions: [
          { name: "Performance Report", href: "/dashboard/content/analytics?view=performance", icon: BarChart3 },
          { name: "Attribution Analysis", href: "/dashboard/content/analytics?view=attribution", icon: Target }
        ]
      }
    ]
  },
  {
    name: "Lead Management",
    items: [
      {
        name: "Leads Dashboard",
        href: "/dashboard/leads",
        icon: Users,
        badge: "8",
        quickActions: [
          { name: "High Priority", href: "/dashboard/leads?priority=high", icon: Zap },
          { name: "Recent Activity", href: "/dashboard/leads?view=recent", icon: MessageSquare }
        ]
      },
      {
        name: "Lead Analytics", 
        href: "/dashboard/leads/analytics",
        icon: BarChart3,
        quickActions: [
          { name: "Conversion Funnel", href: "/dashboard/leads/analytics?view=funnel", icon: TrendingUp },
          { name: "Pipeline Value", href: "/dashboard/leads/analytics?view=pipeline", icon: Target }
        ]
      }
    ]
  },
  {
    name: "System",
    items: [
      {
        name: "Settings",
        href: "/dashboard/settings",
        icon: Settings,
        quickActions: [
          { name: "Profile", href: "/dashboard/settings/profile", icon: User },
          { name: "Integrations", href: "/dashboard/settings/integrations", icon: Database }
        ]
      },
      {
        name: "Help & Support",
        href: "/dashboard/help",
        icon: HelpCircle
      }
    ]
  }
]

interface SidebarNavigationProps {
  className?: string
}

export function SidebarNavigation({ className }: SidebarNavigationProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [activeQuickActions, setActiveQuickActions] = useState<string | null>(null)
  const [showSearch, setShowSearch] = useState(false)
  const pathname = usePathname()
  const { data: session } = useSession()

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) {
        switch (e.key) {
          case 'b':
            e.preventDefault()
            setIsCollapsed(!isCollapsed)
            break
          case 'k':
            e.preventDefault()
            setShowSearch(true)
            break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isCollapsed])

  const toggleQuickActions = (itemName: string) => {
    setActiveQuickActions(activeQuickActions === itemName ? null : itemName)
  }

  return (
    <div
      className={cn(
        "flex flex-col h-screen bg-white border-r border-gray-200 transition-all duration-300 ease-in-out",
        isCollapsed ? "w-16" : "w-72",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        {!isCollapsed && (
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">TechLead</h1>
              <p className="text-xs text-gray-500">AutoPilot</p>
            </div>
          </div>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-2"
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Search Bar */}
      {!isCollapsed && (
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={() => setShowSearch(true)}
            className="w-full flex items-center px-3 py-2 text-sm border border-gray-200 rounded-lg hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors text-left"
          >
            <Search className="w-4 h-4 text-gray-400 mr-3" />
            <span className="text-gray-500">Search... (⌘K)</span>
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-6">
          {navigationSections.map((section) => (
            <div key={section.name}>
              {!isCollapsed && (
                <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  {section.name}
                </h3>
              )}
              <ul className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon
                  const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
                  const hasQuickActions = item.quickActions && item.quickActions.length > 0
                  const showQuickActions = activeQuickActions === item.name && !isCollapsed

                  return (
                    <li key={item.name}>
                      <div
                        className={cn(
                          "group relative flex items-center justify-between px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200",
                          isActive
                            ? "bg-blue-50 text-blue-700 border-r-2 border-blue-700"
                            : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                        )}
                      >
                        <Link
                          href={item.href}
                          className="flex items-center flex-1 min-w-0"
                        >
                          <Icon
                            className={cn(
                              "flex-shrink-0 w-5 h-5 mr-3",
                              isActive ? "text-blue-700" : "text-gray-400"
                            )}
                          />
                          {!isCollapsed && (
                            <>
                              <span className="truncate">{item.name}</span>
                              {item.badge && (
                                <span className="ml-auto inline-block py-0.5 px-2 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
                                  {item.badge}
                                </span>
                              )}
                            </>
                          )}
                        </Link>
                        
                        {!isCollapsed && hasQuickActions && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.preventDefault()
                              toggleQuickActions(item.name)
                            }}
                            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 ml-2"
                          >
                            <Plus className="w-3 h-3" />
                          </Button>
                        )}
                      </div>

                      {/* Quick Actions */}
                      {showQuickActions && (
                        <ul className="mt-1 ml-8 space-y-1">
                          {item.quickActions?.map((action) => {
                            const ActionIcon = action.icon
                            return (
                              <li key={action.name}>
                                <Link
                                  href={action.href}
                                  className="flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors"
                                >
                                  <ActionIcon className="w-4 h-4 mr-3 text-gray-400" />
                                  {action.name}
                                </Link>
                              </li>
                            )
                          })}
                        </ul>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </div>
      </nav>

      {/* User Profile & Actions */}
      <div className="border-t border-gray-200 p-4">
        {!isCollapsed && (
          <div className="mb-4">
            <div className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
              <div className="w-8 h-8 bg-gradient-to-br from-gray-500 to-gray-700 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">
                  {session?.user?.first_name?.[0]}{session?.user?.last_name?.[0]}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {session?.user?.first_name} {session?.user?.last_name}
                </p>
                <p className="text-xs text-gray-500 truncate">
                  {session?.user?.email}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="p-1"
              >
                <Bell className="w-4 h-4 text-gray-400" />
              </Button>
            </div>
          </div>
        )}
        
        <div className="flex items-center space-x-2">
          {isCollapsed ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => signOut({ callbackUrl: "/login" })}
              className="w-full p-2"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          ) : (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="flex-1"
                asChild
              >
                <Link href="/dashboard/settings">
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => signOut({ callbackUrl: "/login" })}
                className="p-2"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Universal Search */}
      <UniversalSearch 
        isOpen={showSearch} 
        onClose={() => setShowSearch(false)} 
      />
    </div>
  )
}