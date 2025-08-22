"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { ContentAnalytics } from '@/lib/api-client'

interface EngagementTrendsChartProps {
  data?: ContentAnalytics
  isLoading: boolean
}

// Mock data for demonstration - in real app this would come from the API
const generateMockData = () => {
  const data = []
  const today = new Date()
  
  for (let i = 29; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)
    
    data.push({
      date: date.toISOString().split('T')[0],
      engagement_rate: Math.random() * 0.06 + 0.02, // 2-8% range
      posts_count: Math.floor(Math.random() * 3) + 1,
      likes: Math.floor(Math.random() * 50) + 10,
      comments: Math.floor(Math.random() * 15) + 2,
      shares: Math.floor(Math.random() * 8) + 1,
    })
  }
  
  return data
}

export function EngagementTrendsChart({ data, isLoading }: EngagementTrendsChartProps) {
  if (isLoading) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading chart data...</div>
      </div>
    )
  }

  // Use mock data for now - replace with real data when available
  const chartData = generateMockData()

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const formatEngagement = (value: number) => {
    return `${(value * 100).toFixed(1)}%`
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900 mb-2">{formatDate(label)}</p>
          <div className="space-y-1">
            <p className="text-sm text-blue-600">
              Engagement Rate: <span className="font-semibold">{formatEngagement(data.engagement_rate)}</span>
            </p>
            <p className="text-sm text-gray-600">
              Posts: <span className="font-semibold">{data.posts_count}</span>
            </p>
            <p className="text-sm text-gray-600">
              Likes: <span className="font-semibold">{data.likes}</span>
            </p>
            <p className="text-sm text-gray-600">
              Comments: <span className="font-semibold">{data.comments}</span>
            </p>
            <p className="text-sm text-gray-600">
              Shares: <span className="font-semibold">{data.shares}</span>
            </p>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="date" 
            tickFormatter={formatDate}
            stroke="#666"
            fontSize={12}
          />
          <YAxis 
            tickFormatter={formatEngagement}
            stroke="#666"
            fontSize={12}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line 
            type="monotone" 
            dataKey="engagement_rate" 
            stroke="#3b82f6" 
            strokeWidth={3}
            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}