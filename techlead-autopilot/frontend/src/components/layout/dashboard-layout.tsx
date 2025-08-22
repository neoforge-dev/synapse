"use client"

import React, { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { SidebarNavigation } from './sidebar-navigation'
import { MobileBottomNavigation } from './mobile-bottom-navigation'
import { BreadcrumbNavigation } from './breadcrumb-navigation'
import { KeyboardShortcuts } from './keyboard-shortcuts'
import { UniversalSearch } from './universal-search'
import { PWAInstallBanner, OfflineIndicator } from '@/components/pwa/pwa-install-banner'
import { ContextualTips, useContextualTips } from '@/components/onboarding/contextual-tips'
import { cn } from '@/lib/utils'

interface DashboardLayoutProps {
  children: React.ReactNode
  title?: string
  description?: string
  className?: string
}

export function DashboardLayout({ 
  children, 
  title, 
  description, 
  className 
}: DashboardLayoutProps) {
  const { data: session, status } = useSession()
  const [isMobile, setIsMobile] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { isEnabled: tipsEnabled } = useContextualTips()

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600 text-sm">Loading...</p>
        </div>
      </div>
    )
  }

  if (status === "unauthenticated") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Access Denied</h1>
          <p className="mt-2 text-gray-600">Please sign in to access this page.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* PWA Components */}
      <PWAInstallBanner />
      <OfflineIndicator />
      
      {/* Sidebar Navigation */}
      {!isMobile && (
        <SidebarNavigation 
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          onOpenSearch={() => setShowSearch(true)}
        />
      )}
      
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Page Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="max-w-7xl mx-auto">
            <BreadcrumbNavigation className="mb-3" />
            {title && (
              <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
            )}
            {description && (
              <p className="mt-1 text-sm text-gray-600">{description}</p>
            )}
          </div>
        </header>
        
        {/* Page Content */}
        <main className={cn("flex-1 overflow-auto", className)}>
          <div className="max-w-7xl mx-auto px-6 py-6">
            {children}
          </div>
        </main>
      </div>
      
      {/* Mobile Navigation */}
      {isMobile && (
        <div className="fixed bottom-0 left-0 right-0 z-50">
          <MobileBottomNavigation />
        </div>
      )}

      {/* Global Components */}
      <UniversalSearch 
        isOpen={showSearch} 
        onClose={() => setShowSearch(false)} 
      />
      <KeyboardShortcuts 
        onOpenSearch={() => setShowSearch(true)}
        onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      
      {/* Contextual Tips System */}
      <ContextualTips isEnabled={tipsEnabled} />
    </div>
  )
}