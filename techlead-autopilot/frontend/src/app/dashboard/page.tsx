"use client"

import { useSession, signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function DashboardPage() {
  const { data: session, status } = useSession()

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

  if (status === "unauthenticated") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Access Denied</h1>
          <p className="mt-2 text-gray-600">Please sign in to access this page.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                TechLead AutoPilot
              </h1>
              <p className="text-sm text-gray-600">
                Welcome back, {session?.user?.first_name}!
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                {session?.user?.first_name} {session?.user?.last_name}
              </span>
              <Button
                variant="outline"
                onClick={() => signOut({ callbackUrl: "/login" })}
              >
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* User Info Card */}
            <Card>
              <CardHeader>
                <CardTitle>Account Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div>
                  <p className="text-sm font-medium text-gray-500">Name</p>
                  <p className="text-gray-900">
                    {session?.user?.first_name} {session?.user?.last_name}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Email</p>
                  <p className="text-gray-900">{session?.user?.email}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Role</p>
                  <p className="text-gray-900 capitalize">{session?.user?.role}</p>
                </div>
                {session?.user?.job_title && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">Job Title</p>
                    <p className="text-gray-900">{session?.user?.job_title}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Content Generation Card */}
            <Card>
              <CardHeader>
                <CardTitle>Content Generation</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-4">
                  Generate high-quality LinkedIn content automatically.
                </p>
                <div className="space-y-2">
                  <Button className="w-full" onClick={() => window.location.href = '/dashboard/content/generate'}>
                    Generate New Content
                  </Button>
                  <Button variant="outline" className="w-full" onClick={() => window.location.href = '/dashboard/content'}>
                    Manage Content
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Leads Card */}
            <Card>
              <CardHeader>
                <CardTitle>Lead Detection</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-4">
                  Track and manage consultation opportunities.
                </p>
                <Button variant="outline" className="w-full">
                  View Leads
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Recent Activity Placeholder */}
          <div className="mt-8">
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <p className="text-gray-500">No recent activity to display.</p>
                  <p className="text-sm text-gray-400 mt-2">
                    Start by generating your first piece of content!
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}