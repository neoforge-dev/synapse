"use client"

import { useQuery } from "@tanstack/react-query"
import { contentApi, ContentType } from "@/lib/api-client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2, Lightbulb, Users, Zap, TrendingUp, Building, Code, Puzzle, Rocket } from "lucide-react"
import { cn } from "@/lib/utils"

interface ContentTypeSelectorProps {
  selectedType?: string
  onSelect: (contentType: string) => void
  className?: string
}

const contentTypeIcons: Record<string, React.ComponentType<any>> = {
  technical_insight: Lightbulb,
  leadership_story: Users,
  controversial_take: Zap,
  career_advice: TrendingUp,
  nobuild_philosophy: Building,
  architecture_review: Code,
  team_building: Puzzle,
  startup_scaling: Rocket,
}

export function ContentTypeSelector({ selectedType, onSelect, className }: ContentTypeSelectorProps) {
  const { data: contentTypes, isLoading, error } = useQuery({
    queryKey: ['content-types'],
    queryFn: () => contentApi.getTypes(),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2 text-sm text-gray-600">Loading content types...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center p-8">
        <p className="text-red-600">Failed to load content types</p>
        <p className="text-sm text-gray-500 mt-1">Please try again later</p>
      </div>
    )
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Choose Content Type
        </h3>
        <p className="text-sm text-gray-600">
          Select from 8 proven templates that generated €290K in consultation pipeline
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {contentTypes?.content_types.map((contentType: ContentType) => {
          const Icon = contentTypeIcons[contentType.value] || Lightbulb
          const isSelected = selectedType === contentType.value

          return (
            <Card
              key={contentType.value}
              className={cn(
                "cursor-pointer transition-all duration-200 hover:shadow-lg",
                isSelected 
                  ? "ring-2 ring-blue-500 border-blue-200 bg-blue-50" 
                  : "hover:border-gray-300"
              )}
              onClick={() => onSelect(contentType.value)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Icon className={cn(
                      "h-5 w-5",
                      isSelected ? "text-blue-600" : "text-gray-600"
                    )} />
                    <CardTitle className="text-base">{contentType.name}</CardTitle>
                  </div>
                  {isSelected && (
                    <Badge variant="default" className="bg-blue-600">
                      Selected
                    </Badge>
                  )}
                </div>
                <CardDescription className="text-sm">
                  {contentType.description}
                </CardDescription>
              </CardHeader>
              
              <CardContent className="pt-0">
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-medium text-gray-700 mb-1">Optimal Length</p>
                    <Badge variant="outline" className="text-xs">
                      {contentType.optimal_length}
                    </Badge>
                  </div>
                  
                  <div>
                    <p className="text-xs font-medium text-gray-700 mb-1">Target Audience</p>
                    <p className="text-xs text-gray-600">{contentType.target_audience}</p>
                  </div>
                  
                  <div>
                    <p className="text-xs font-medium text-gray-700 mb-1">Example Topics</p>
                    <div className="flex flex-wrap gap-1">
                      {contentType.example_topics.slice(0, 2).map((topic, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">
                          {topic}
                        </Badge>
                      ))}
                      {contentType.example_topics.length > 2 && (
                        <Badge variant="secondary" className="text-xs">
                          +{contentType.example_topics.length - 2} more
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}