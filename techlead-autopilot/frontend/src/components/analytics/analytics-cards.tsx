"use client"

import { TrendingUp, TrendingDown } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface AnalyticsCardProps {
  title: string
  value: string | number
  description?: string
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon?: React.ComponentType<any>
  isLoading?: boolean
}

export function AnalyticsCard({
  title,
  value,
  description,
  change,
  changeType = 'neutral',
  icon: Icon,
  isLoading = false
}: AnalyticsCardProps) {
  const getTrendIcon = () => {
    if (changeType === 'positive') return <TrendingUp className="h-4 w-4 text-green-600" />
    if (changeType === 'negative') return <TrendingDown className="h-4 w-4 text-red-600" />
    return null
  }

  const getChangeColor = () => {
    if (changeType === 'positive') return 'text-green-600 border-green-200'
    if (changeType === 'negative') return 'text-red-600 border-red-200'
    return 'text-gray-600 border-gray-200'
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-gray-600">
          {title}
        </CardTitle>
        {Icon && (
          <Icon className="h-4 w-4 text-gray-400" />
        )}
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-bold text-gray-900">
              {isLoading ? (
                <div className="h-8 bg-gray-200 rounded animate-pulse w-16"></div>
              ) : (
                value
              )}
            </div>
            {change && (
              <Badge variant="outline" className={getChangeColor()}>
                <div className="flex items-center gap-1">
                  {getTrendIcon()}
                  <span className="text-xs">{change}</span>
                </div>
              </Badge>
            )}
          </div>
          {description && (
            <p className="text-xs text-gray-500">{description}</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

interface AnalyticsCardsProps {
  cards: AnalyticsCardProps[]
  isLoading?: boolean
}

export function AnalyticsCards({ cards, isLoading = false }: AnalyticsCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
      {cards.map((card, index) => (
        <AnalyticsCard
          key={index}
          {...card}
          isLoading={isLoading}
        />
      ))}
    </div>
  )
}