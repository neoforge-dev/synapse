"use client"

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { HelpCenter } from '@/components/help/help-center'

function HelpPageContent() {
  const searchParams = useSearchParams()
  const initialSearch = searchParams?.get('search') || ''
  const article = searchParams?.get('article') || ''

  return (
    <DashboardLayout
      title="Help Center"
      description="Find answers, learn best practices, and get the most out of your technical leadership platform"
    >
      <HelpCenter 
        initialSearchQuery={initialSearch}
        showCategories={true}
      />
    </DashboardLayout>
  )
}

export default function HelpPage() {
  return (
    <Suspense fallback={
      <DashboardLayout
        title="Help Center"
        description="Loading help center..."
      >
        <div className="flex items-center justify-center min-h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </DashboardLayout>
    }>
      <HelpPageContent />
    </Suspense>
  )
}