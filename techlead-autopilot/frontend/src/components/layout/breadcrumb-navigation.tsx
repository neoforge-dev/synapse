"use client"

import React from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { ChevronRight, Home } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BreadcrumbItem {
  name: string
  href: string
  icon?: React.ComponentType<{ className?: string }>
}

interface BreadcrumbNavigationProps {
  customBreadcrumbs?: BreadcrumbItem[]
  className?: string
}

// Route mapping for generating breadcrumbs
const routeMap: Record<string, string> = {
  'dashboard': 'Dashboard',
  'content': 'Content Library',
  'generate': 'Generate Content',
  'analytics': 'Analytics',
  'leads': 'Lead Management',
  'settings': 'Settings',
  'profile': 'Profile',
  'integrations': 'Integrations',
  'help': 'Help & Support'
}

// Special route configurations
const specialRoutes: Record<string, { name: string; parent?: string }> = {
  '/dashboard/content/generate': { name: 'Generate Content', parent: '/dashboard/content' },
  '/dashboard/content/analytics': { name: 'Content Analytics', parent: '/dashboard/content' },
  '/dashboard/leads/analytics': { name: 'Lead Analytics', parent: '/dashboard/leads' },
  '/dashboard/settings/profile': { name: 'Profile Settings', parent: '/dashboard/settings' },
  '/dashboard/settings/integrations': { name: 'Integrations', parent: '/dashboard/settings' }
}

export function BreadcrumbNavigation({ 
  customBreadcrumbs, 
  className 
}: BreadcrumbNavigationProps) {
  const pathname = usePathname()

  // Generate breadcrumbs from current path
  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    if (customBreadcrumbs) {
      return customBreadcrumbs
    }

    // Check for special routes first
    if (specialRoutes[pathname]) {
      const special = specialRoutes[pathname]
      const breadcrumbs: BreadcrumbItem[] = [
        { name: 'Dashboard', href: '/dashboard', icon: Home }
      ]

      if (special.parent) {
        const parentSegments = special.parent.split('/').filter(Boolean)
        let currentPath = ''
        
        parentSegments.forEach((segment, index) => {
          currentPath += `/${segment}`
          if (index > 0) { // Skip 'dashboard' as it's already added
            breadcrumbs.push({
              name: routeMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1),
              href: currentPath
            })
          }
        })
      }

      breadcrumbs.push({
        name: special.name,
        href: pathname
      })

      return breadcrumbs
    }

    // Generate from path segments
    const segments = pathname.split('/').filter(Boolean)
    const breadcrumbs: BreadcrumbItem[] = []
    let currentPath = ''

    segments.forEach((segment, index) => {
      currentPath += `/${segment}`
      
      if (index === 0 && segment === 'dashboard') {
        breadcrumbs.push({
          name: 'Dashboard',
          href: currentPath,
          icon: Home
        })
      } else {
        breadcrumbs.push({
          name: routeMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1),
          href: currentPath
        })
      }
    })

    return breadcrumbs
  }

  const breadcrumbs = generateBreadcrumbs()

  // Don't show breadcrumbs if we're just on dashboard
  if (breadcrumbs.length <= 1) {
    return null
  }

  return (
    <nav className={cn("flex items-center space-x-1 text-sm text-gray-500", className)}>
      {breadcrumbs.map((item, index) => {
        const isLast = index === breadcrumbs.length - 1
        const Icon = item.icon

        return (
          <div key={item.href} className="flex items-center">
            {index > 0 && (
              <ChevronRight className="w-4 h-4 mx-2 text-gray-400" />
            )}
            
            {isLast ? (
              <span className="font-medium text-gray-900 flex items-center">
                {Icon && <Icon className="w-4 h-4 mr-1" />}
                {item.name}
              </span>
            ) : (
              <Link
                href={item.href}
                className="hover:text-gray-700 transition-colors flex items-center"
              >
                {Icon && <Icon className="w-4 h-4 mr-1" />}
                {item.name}
              </Link>
            )}
          </div>
        )
      })}
    </nav>
  )
}

// Hook for getting current breadcrumbs (useful for page titles)
export function useBreadcrumbs(customBreadcrumbs?: BreadcrumbItem[]) {
  const pathname = usePathname()
  
  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    if (customBreadcrumbs) {
      return customBreadcrumbs
    }

    if (specialRoutes[pathname]) {
      const special = specialRoutes[pathname]
      const breadcrumbs: BreadcrumbItem[] = [
        { name: 'Dashboard', href: '/dashboard', icon: Home }
      ]

      if (special.parent) {
        const parentSegments = special.parent.split('/').filter(Boolean)
        let currentPath = ''
        
        parentSegments.forEach((segment, index) => {
          currentPath += `/${segment}`
          if (index > 0) {
            breadcrumbs.push({
              name: routeMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1),
              href: currentPath
            })
          }
        })
      }

      breadcrumbs.push({
        name: special.name,
        href: pathname
      })

      return breadcrumbs
    }

    const segments = pathname.split('/').filter(Boolean)
    const breadcrumbs: BreadcrumbItem[] = []
    let currentPath = ''

    segments.forEach((segment, index) => {
      currentPath += `/${segment}`
      
      if (index === 0 && segment === 'dashboard') {
        breadcrumbs.push({
          name: 'Dashboard',
          href: currentPath,
          icon: Home
        })
      } else {
        breadcrumbs.push({
          name: routeMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1),
          href: currentPath
        })
      }
    })

    return breadcrumbs
  }

  return generateBreadcrumbs()
}