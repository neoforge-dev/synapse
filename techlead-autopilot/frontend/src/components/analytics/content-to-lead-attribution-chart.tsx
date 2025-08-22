"use client"

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, Users, DollarSign, Target } from 'lucide-react'

interface ContentToLeadAttributionChartProps {
  data?: any
  isLoading: boolean
  timeRange: number
}

// Mock attribution data showing content performance
const generateMockAttributionData = () => {
  const contentTypes = [
    'Technical Insight',
    'Leadership Story', 
    'Controversial Take',
    'Career Advice',
    'Architecture Review',
    'Team Building',
  ]

  return contentTypes.map(type => ({
    contentType: type,
    posts: Math.floor(Math.random() * 8) + 3,
    leads: Math.floor(Math.random() * 15) + 2,
    value: Math.floor(Math.random() * 25000) + 5000,
    conversionRate: (Math.random() * 0.04) + 0.01, // 1-5%
  }))
}

const mockTopPerformers = [
  {
    id: "1",
    title: "How I scaled our engineering team from 5 to 50 developers",
    contentType: "Leadership Story",
    leads: 8,
    value: 15000,
    engagement: 0.067,
    publishedDate: "2024-01-15"
  },
  {
    id: "2", 
    title: "Why microservices are often the wrong choice",
    contentType: "Controversial Take",
    leads: 6,
    value: 12000,
    engagement: 0.058,
    publishedDate: "2024-01-10"
  },
  {
    id: "3",
    title: "The hidden costs of technical debt",
    contentType: "Technical Insight", 
    leads: 7,
    value: 18000,
    engagement: 0.042,
    publishedDate: "2024-01-08"
  },
]

export function ContentToLeadAttributionChart({ data, isLoading, timeRange }: ContentToLeadAttributionChartProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="h-80 flex items-center justify-center">
            <div className="animate-pulse text-gray-400">Loading attribution data...</div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const chartData = generateMockAttributionData()
  const topPerformers = mockTopPerformers

  const formatValue = (value: number) => `€${(value / 1000).toFixed(0)}K`
  const formatRate = (value: number) => `${(value * 100).toFixed(1)}%`

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900 mb-2">{label}</p>
          <div className="space-y-1">
            <p className="text-sm text-blue-600">
              Posts: <span className="font-semibold">{data.posts}</span>
            </p>
            <p className="text-sm text-green-600">
              Leads: <span className="font-semibold">{data.leads}</span>
            </p>
            <p className="text-sm text-purple-600">
              Pipeline Value: <span className="font-semibold">{formatValue(data.value)}</span>
            </p>
            <p className="text-sm text-orange-600">
              Conversion Rate: <span className="font-semibold">{formatRate(data.conversionRate)}</span>
            </p>
          </div>
        </div>
      )
    }
    return null
  }

  const totalLeads = chartData.reduce((sum, item) => sum + item.leads, 0)
  const totalValue = chartData.reduce((sum, item) => sum + item.value, 0)
  const avgConversionRate = chartData.reduce((sum, item) => sum + item.conversionRate, 0) / chartData.length

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Leads</p>
                <p className="text-2xl font-bold text-gray-900">{totalLeads}</p>
              </div>
              <Users className="h-8 w-8 text-blue-600" />
            </div>
            <p className="text-xs text-gray-500 mt-1">From content in last {timeRange} days</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Pipeline Value</p>
                <p className="text-2xl font-bold text-gray-900">{formatValue(totalValue)}</p>
              </div>
              <DollarSign className="h-8 w-8 text-green-600" />
            </div>
            <p className="text-xs text-gray-500 mt-1">Total estimated value</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Conversion</p>
                <p className="text-2xl font-bold text-gray-900">{formatRate(avgConversionRate)}</p>
              </div>
              <Target className="h-8 w-8 text-purple-600" />
            </div>
            <p className="text-xs text-gray-500 mt-1">Content to lead rate</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Value per Lead</p>
                <p className="text-2xl font-bold text-gray-900">€{Math.round(totalValue / totalLeads).toLocaleString()}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-orange-600" />
            </div>
            <p className="text-xs text-gray-500 mt-1">Average lead value</p>
          </CardContent>
        </Card>
      </div>

      {/* Attribution Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Content Type Attribution</CardTitle>
          <CardDescription>
            Lead generation performance by content type over the last {timeRange} days
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="contentType" 
                  stroke="#666"
                  fontSize={12}
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis stroke="#666" fontSize={12} />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Bar dataKey="posts" fill="#3b82f6" name="Posts" />
                <Bar dataKey="leads" fill="#10b981" name="Leads" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Top Performing Content */}
      <Card>
        <CardHeader>
          <CardTitle>Top Performing Content</CardTitle>
          <CardDescription>
            Individual posts that generated the most leads and pipeline value
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {topPerformers.map((post, index) => (
              <div key={post.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge variant="outline">#{index + 1}</Badge>
                    <Badge variant="secondary">{post.contentType}</Badge>
                    <span className="text-sm text-gray-500">
                      {new Date(post.publishedDate).toLocaleDateString()}
                    </span>
                  </div>
                  <h4 className="font-medium text-gray-900 mb-1">{post.title}</h4>
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>👥 {post.leads} leads</span>
                    <span>💰 {formatValue(post.value)} value</span>
                    <span>📈 {formatRate(post.engagement)} engagement</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-green-600">{formatValue(post.value)}</div>
                  <div className="text-sm text-gray-500">{post.leads} leads</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Attribution Insights */}
      <Card>
        <CardHeader>
          <CardTitle>Attribution Insights</CardTitle>
          <CardDescription>
            Key insights from content-to-lead attribution analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Best Performing Types</h4>
              <div className="space-y-2">
                {chartData
                  .sort((a, b) => b.conversionRate - a.conversionRate)
                  .slice(0, 3)
                  .map((type, index) => (
                    <div key={type.contentType} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{type.contentType}</span>
                      <Badge variant="outline">{formatRate(type.conversionRate)}</Badge>
                    </div>
                  ))}
              </div>
            </div>
            
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Optimization Opportunities</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Controversial takes generate 40% more engagement</li>
                <li>• Leadership stories have highest conversion rates</li>
                <li>• Technical insights attract enterprise leads</li>
                <li>• Career advice resonates with mid-level managers</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}