"use client"

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

interface ContentTypeData {
  content_type: string
  count: number
  avg_engagement: number
}

interface ContentTypePerformanceChartProps {
  data?: ContentTypeData[]
  isLoading: boolean
}

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green  
  '#f59e0b', // yellow
  '#ef4444', // red
  '#8b5cf6', // purple
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
]

const mockData: ContentTypeData[] = [
  { content_type: 'technical_insight', count: 12, avg_engagement: 0.045 },
  { content_type: 'leadership_story', count: 8, avg_engagement: 0.038 },
  { content_type: 'controversial_take', count: 6, avg_engagement: 0.052 },
  { content_type: 'career_advice', count: 10, avg_engagement: 0.041 },
  { content_type: 'architecture_review', count: 5, avg_engagement: 0.033 },
  { content_type: 'team_building', count: 7, avg_engagement: 0.036 },
]

export function ContentTypePerformanceChart({ data, isLoading }: ContentTypePerformanceChartProps) {
  if (isLoading) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading chart data...</div>
      </div>
    )
  }

  // Use mock data for now - replace with real data when available
  const chartData = (data || mockData).map(item => ({
    name: item.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value: item.count,
    engagement: item.avg_engagement,
    originalName: item.content_type,
  }))

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900 mb-2">{data.name}</p>
          <div className="space-y-1">
            <p className="text-sm text-gray-600">
              Posts: <span className="font-semibold">{data.value}</span>
            </p>
            <p className="text-sm text-gray-600">
              Avg Engagement: <span className="font-semibold">{(data.engagement * 100).toFixed(1)}%</span>
            </p>
            <p className="text-sm text-gray-600">
              Share: <span className="font-semibold">{((data.value / chartData.reduce((sum, item) => sum + item.value, 0)) * 100).toFixed(1)}%</span>
            </p>
          </div>
        </div>
      )
    }
    return null
  }

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    if (percent < 0.05) return null // Don't show labels for slices smaller than 5%
    
    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        fontSize={12}
        fontWeight="600"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    )
  }

  const CustomLegend = ({ payload }: any) => {
    return (
      <div className="flex flex-wrap justify-center gap-4 mt-4">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm text-gray-600">{entry.value}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}