"use client"

import { useEffect } from 'react'
import { initPerformanceOptimizations } from '@/lib/performance'
import { initAccessibilityFeatures } from '@/lib/accessibility'

export function PerformanceProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize performance optimizations
    initPerformanceOptimizations()
    
    // Initialize accessibility features
    initAccessibilityFeatures()
  }, [])

  return <>{children}</>
}