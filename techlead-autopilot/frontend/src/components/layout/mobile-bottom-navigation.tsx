"use client"

import React, { useState, useRef, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  FileText,
  Users,
  BarChart3,
  Plus,
  Menu,
  X
} from 'lucide-react'

interface MobileNavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string | number
}

const mainNavItems: MobileNavItem[] = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard
  },
  {
    name: "Content",
    href: "/dashboard/content",
    icon: FileText,
    badge: "12"
  },
  {
    name: "Leads",
    href: "/dashboard/leads", 
    icon: Users,
    badge: "8"
  },
  {
    name: "Analytics",
    href: "/dashboard/content/analytics",
    icon: BarChart3
  }
]

const quickActions = [
  { name: "Generate Content", href: "/dashboard/content/generate", icon: FileText },
  { name: "View High Priority Leads", href: "/dashboard/leads?priority=high", icon: Users },
  { name: "Content Analytics", href: "/dashboard/content/analytics", icon: BarChart3 },
  { name: "Lead Analytics", href: "/dashboard/leads/analytics", icon: BarChart3 }
]

interface MobileBottomNavigationProps {
  className?: string
}

export function MobileBottomNavigation({ className }: MobileBottomNavigationProps) {
  const [showQuickActions, setShowQuickActions] = useState(false)
  const [gestureStart, setGestureStart] = useState<{ x: number; y: number } | null>(null)
  const pathname = usePathname()
  const quickActionsRef = useRef<HTMLDivElement>(null)

  // Handle touch gestures for quick actions
  useEffect(() => {
    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        setGestureStart({ x: e.touches[0].clientX, y: e.touches[0].clientY })
      }
    }

    const handleTouchEnd = (e: TouchEvent) => {
      if (gestureStart && e.changedTouches.length === 1) {
        const touch = e.changedTouches[0]
        const deltaY = gestureStart.y - touch.clientY
        const deltaX = Math.abs(gestureStart.x - touch.clientX)
        
        // Upward swipe gesture to show quick actions
        if (deltaY > 50 && deltaX < 100 && touch.clientY > window.innerHeight - 150) {
          setShowQuickActions(true)
        }
      }
      setGestureStart(null)
    }

    document.addEventListener('touchstart', handleTouchStart)
    document.addEventListener('touchend', handleTouchEnd)
    
    return () => {
      document.removeEventListener('touchstart', handleTouchStart)
      document.removeEventListener('touchend', handleTouchEnd)
    }
  }, [gestureStart])

  // Close quick actions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (quickActionsRef.current && !quickActionsRef.current.contains(event.target as Node)) {
        setShowQuickActions(false)
      }
    }

    if (showQuickActions) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showQuickActions])

  return (
    <>
      {/* Quick Actions Overlay */}
      {showQuickActions && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40 flex items-end">
          <div
            ref={quickActionsRef}
            className="bg-white rounded-t-3xl w-full p-6 transform transition-transform duration-300 ease-out"
            style={{
              animation: showQuickActions ? 'slideUp 0.3s ease-out' : undefined
            }}
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Quick Actions</h3>
              <button
                onClick={() => setShowQuickActions(false)}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              {quickActions.map((action) => {
                const Icon = action.icon
                return (
                  <Link
                    key={action.name}
                    href={action.href}
                    onClick={() => setShowQuickActions(false)}
                    className="flex flex-col items-center p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                  >
                    <Icon className="w-6 h-6 text-blue-600 mb-2" />
                    <span className="text-sm font-medium text-gray-900 text-center">
                      {action.name}
                    </span>
                  </Link>
                )
              })}
            </div>
            
            <div className="mt-6 text-center">
              <p className="text-xs text-gray-500">
                Swipe up from bottom for quick access
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Navigation Bar */}
      <nav className={cn(
        "bg-white border-t border-gray-200 px-4 py-2 flex items-center justify-around safe-area-pb",
        className
      )}>
        {mainNavItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center p-2 rounded-lg transition-all duration-200 relative min-w-0 flex-1",
                isActive
                  ? "text-blue-600"
                  : "text-gray-400 hover:text-gray-600 active:text-blue-600"
              )}
            >
              <div className="relative">
                <Icon className="w-6 h-6" />
                {item.badge && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-4 w-4 flex items-center justify-center">
                    {item.badge}
                  </span>
                )}
              </div>
              <span className="text-xs mt-1 font-medium truncate">
                {item.name}
              </span>
            </Link>
          )
        })}
        
        {/* Quick Actions Trigger */}
        <button
          onClick={() => setShowQuickActions(true)}
          className={cn(
            "flex flex-col items-center justify-center p-2 rounded-lg transition-all duration-200 min-w-0 flex-1",
            showQuickActions
              ? "text-blue-600 bg-blue-50"
              : "text-gray-400 hover:text-gray-600 active:text-blue-600"
          )}
        >
          <div className="relative">
            <Plus className="w-6 h-6" />
          </div>
          <span className="text-xs mt-1 font-medium">
            More
          </span>
        </button>
      </nav>

      <style jsx>{`
        @keyframes slideUp {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }
        
        .safe-area-pb {
          padding-bottom: env(safe-area-inset-bottom);
        }
      `}</style>
    </>
  )
}