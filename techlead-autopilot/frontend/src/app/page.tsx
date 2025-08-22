"use client"

import { useSession } from "next-auth/react"
import { useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function Home() {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === "authenticated") {
      router.push("/dashboard")
    }
  }, [status, router])

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (status === "authenticated") {
    return null // Will redirect to dashboard
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="pt-8 pb-12">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                TechLead AutoPilot
              </h1>
            </div>
            <div className="space-x-4">
              <Link href="/login">
                <Button variant="outline">Sign In</Button>
              </Link>
              <Link href="/register">
                <Button>Get Started</Button>
              </Link>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <main className="pt-16 pb-24">
          <div className="text-center">
            <h2 className="text-5xl font-extrabold text-gray-900 sm:text-6xl">
              Automate Your
              <span className="text-blue-600"> LinkedIn Presence</span>
            </h2>
            <p className="mt-6 text-xl text-gray-600 max-w-3xl mx-auto">
              Generate high-quality LinkedIn content and detect consultation opportunities 
              automatically. Turn your expertise into a consistent lead generation machine.
            </p>
            
            <div className="mt-10 flex justify-center space-x-6">
              <Link href="/register">
                <Button size="lg" className="px-8 py-3">
                  Start Free Trial
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="outline" size="lg" className="px-8 py-3">
                  Sign In
                </Button>
              </Link>
            </div>
          </div>

          {/* Features */}
          <div className="mt-24">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="bg-blue-100 rounded-full p-3 w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Automated Content
                </h3>
                <p className="text-gray-600">
                  Generate high-quality LinkedIn posts automatically using proven templates 
                  that drive engagement and consultation inquiries.
                </p>
              </div>

              <div className="text-center">
                <div className="bg-green-100 rounded-full p-3 w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Lead Detection
                </h3>
                <p className="text-gray-600">
                  AI-powered system detects consultation opportunities from LinkedIn 
                  engagement with 85%+ accuracy and priority scoring.
                </p>
              </div>

              <div className="text-center">
                <div className="bg-purple-100 rounded-full p-3 w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Revenue Growth
                </h3>
                <p className="text-gray-600">
                  Based on proven algorithms that generated €290K in consultation 
                  pipeline value for technical consultants.
                </p>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
