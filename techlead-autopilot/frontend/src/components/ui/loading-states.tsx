"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { Loader2, FileText, Users, BarChart3, Settings, Sparkles } from 'lucide-react'

interface LoadingSkeletonProps {
  className?: string
}

// Generic loading skeleton
export function LoadingSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div className={cn("animate-pulse", className)}>
      <div className="bg-gray-200 rounded h-4 w-3/4 mb-2"></div>
      <div className="bg-gray-200 rounded h-4 w-1/2"></div>
    </div>
  )
}

// Card loading skeleton
export function LoadingCard({ className }: LoadingSkeletonProps) {
  return (
    <div className={cn("border rounded-lg p-6 space-y-3", className)}>
      <div className="animate-pulse">
        <div className="flex items-center space-x-3 mb-4">
          <div className="bg-gray-200 rounded-full h-10 w-10"></div>
          <div className="flex-1">
            <div className="bg-gray-200 rounded h-4 w-24 mb-1"></div>
            <div className="bg-gray-200 rounded h-3 w-32"></div>
          </div>
        </div>
        <div className="space-y-2">
          <div className="bg-gray-200 rounded h-4 w-full"></div>
          <div className="bg-gray-200 rounded h-4 w-3/4"></div>
          <div className="bg-gray-200 rounded h-4 w-1/2"></div>
        </div>
      </div>
    </div>
  )
}

// Dashboard loading state
export function DashboardLoading() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="animate-pulse">
        <div className="bg-gray-200 rounded h-8 w-64 mb-2"></div>
        <div className="bg-gray-200 rounded h-4 w-96"></div>
      </div>

      {/* Stats cards skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <LoadingCard key={i} />
        ))}
      </div>

      {/* Content area skeleton */}
      <LoadingCard className="h-64" />
    </div>
  )
}

// Content list loading
export function ContentListLoading() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="border rounded-lg p-4">
          <div className="animate-pulse">
            <div className="flex items-center space-x-3 mb-3">
              <div className="bg-gray-200 rounded h-6 w-6"></div>
              <div className="bg-gray-200 rounded h-4 w-32"></div>
              <div className="bg-gray-200 rounded-full h-5 w-12"></div>
            </div>
            <div className="space-y-2">
              <div className="bg-gray-200 rounded h-4 w-full"></div>
              <div className="bg-gray-200 rounded h-4 w-2/3"></div>
            </div>
            <div className="flex items-center space-x-4 mt-3">
              <div className="bg-gray-200 rounded h-3 w-16"></div>
              <div className="bg-gray-200 rounded h-3 w-20"></div>
              <div className="bg-gray-200 rounded h-3 w-12"></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// Leads list loading
export function LeadsListLoading() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="border rounded-lg p-4">
          <div className="animate-pulse">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="bg-gray-200 rounded-full h-10 w-10"></div>
                <div>
                  <div className="bg-gray-200 rounded h-4 w-24 mb-1"></div>
                  <div className="bg-gray-200 rounded h-3 w-32"></div>
                </div>
              </div>
              <div className="text-right space-y-1">
                <div className="bg-gray-200 rounded h-3 w-12"></div>
                <div className="bg-gray-200 rounded h-4 w-16"></div>
              </div>
            </div>
            <div className="mt-3 bg-gray-200 rounded h-3 w-3/4"></div>
          </div>
        </div>
      ))}
    </div>
  )
}

// Analytics loading
export function AnalyticsLoading() {
  return (
    <div className="space-y-6">
      {/* Stats overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border rounded-lg p-4">
            <div className="animate-pulse">
              <div className="bg-gray-200 rounded h-6 w-6 mb-2"></div>
              <div className="bg-gray-200 rounded h-6 w-12 mb-1"></div>
              <div className="bg-gray-200 rounded h-3 w-16"></div>
            </div>
          </div>
        ))}
      </div>

      {/* Chart skeletons */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="border rounded-lg p-6">
          <div className="animate-pulse">
            <div className="bg-gray-200 rounded h-5 w-32 mb-4"></div>
            <div className="bg-gray-200 rounded h-64 w-full"></div>
          </div>
        </div>
        <div className="border rounded-lg p-6">
          <div className="animate-pulse">
            <div className="bg-gray-200 rounded h-5 w-28 mb-4"></div>
            <div className="bg-gray-200 rounded h-64 w-full"></div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Spinner with message
interface SpinnerProps {
  message?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Spinner({ message = "Loading...", size = 'md', className }: SpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  }

  return (
    <div className={cn("flex items-center justify-center space-x-2", className)}>
      <Loader2 className={cn("animate-spin text-blue-600", sizeClasses[size])} />
      {message && <span className="text-gray-600 text-sm">{message}</span>}
    </div>
  )
}

// Loading page wrapper
interface LoadingPageProps {
  title?: string
  description?: string
  icon?: React.ComponentType<{ className?: string }>
  children?: React.ReactNode
}

export function LoadingPage({ title, description, icon: Icon, children }: LoadingPageProps) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        {Icon && (
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Icon className="w-8 h-8 text-blue-600" />
          </div>
        )}
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        {title && <h1 className="text-xl font-semibold text-gray-900 mb-2">{title}</h1>}
        {description && <p className="text-gray-600 mb-4">{description}</p>}
        {children}
      </div>
    </div>
  )
}

// Progressive loading component
interface ProgressiveLoadingProps {
  isLoading: boolean
  children: React.ReactNode
  fallback: React.ReactNode
  delay?: number
}

export function ProgressiveLoading({ 
  isLoading, 
  children, 
  fallback, 
  delay = 200 
}: ProgressiveLoadingProps) {
  const [showFallback, setShowFallback] = React.useState(false)

  React.useEffect(() => {
    if (isLoading) {
      const timer = setTimeout(() => setShowFallback(true), delay)
      return () => clearTimeout(timer)
    } else {
      setShowFallback(false)
    }
  }, [isLoading, delay])

  if (isLoading && showFallback) {
    return <>{fallback}</>
  }

  if (isLoading && !showFallback) {
    return null
  }

  return <>{children}</>
}

// Page transition loading
export function PageTransition({ isLoading }: { isLoading: boolean }) {
  if (!isLoading) return null

  return (
    <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
        <p className="text-sm text-gray-600">Loading...</p>
      </div>
    </div>
  )
}