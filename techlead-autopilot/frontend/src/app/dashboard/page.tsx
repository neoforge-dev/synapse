"use client"

import { useSession } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import Link from "next/link"

export default function DashboardPage() {
  const { data: session } = useSession()

  return (
    <DashboardLayout
      title="Welcome back!"
      description={`Good to see you, ${session?.user?.first_name}. Here's what's happening with your technical leadership platform.`}
    >
      <div className="space-y-6">
        {/* Overview Cards */}
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
                <Button className="w-full" asChild>
                  <Link href="/dashboard/content/generate">
                    Generate New Content
                  </Link>
                </Button>
                <Button variant="outline" className="w-full" asChild>
                  <Link href="/dashboard/content">
                    Manage Content
                  </Link>
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
              <Button variant="outline" className="w-full" asChild>
                <Link href="/dashboard/leads">
                  View Leads
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
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
        </div>
      </div>
    </DashboardLayout>
  )
}