"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, CheckCircle2, ExternalLink } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ContentGenerationForm } from "@/components/content/content-generation-form"
import { ContentGenerated } from "@/lib/api-client"

export default function GenerateContentPage() {
  const [generatedContent, setGeneratedContent] = useState<ContentGenerated | null>(null)
  const router = useRouter()

  const handleGenerationSuccess = (content: ContentGenerated) => {
    setGeneratedContent(content)
  }

  const resetForm = () => {
    setGeneratedContent(null)
  }

  if (generatedContent) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8">
            <Link 
              href="/dashboard/content" 
              className="inline-flex items-center text-sm text-blue-600 hover:text-blue-500 mb-4"
            >
              <ArrowLeft className="mr-1 h-4 w-4" />
              Back to Content
            </Link>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Content Generated Successfully!</h1>
                <p className="mt-2 text-gray-600">
                  Your content has been created and is ready for review and approval.
                </p>
              </div>
              <CheckCircle2 className="h-12 w-12 text-green-500" />
            </div>
          </div>

          {/* Generated Content Preview */}
          <Card className="mb-8">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {generatedContent.topic}
                    <Badge variant="outline">
                      {generatedContent.content_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    Engagement Prediction: {(generatedContent.engagement_prediction * 100).toFixed(1)}% • 
                    {generatedContent.character_count} characters • 
                    {generatedContent.estimated_read_time_seconds}s read time
                  </CardDescription>
                </div>
                <Badge 
                  variant={generatedContent.status === 'draft' ? 'secondary' : 'default'}
                  className="ml-2"
                >
                  {generatedContent.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </Badge>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-6">
              {/* Hook */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Hook</h4>
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-md">
                  <p className="text-gray-800">{generatedContent.hook}</p>
                </div>
              </div>

              {/* Body */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Body</h4>
                <div className="bg-gray-50 p-4 rounded-md">
                  <p className="text-gray-800 whitespace-pre-line">{generatedContent.body}</p>
                </div>
              </div>

              {/* Call to Action */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Call to Action</h4>
                <div className="bg-green-50 border-l-4 border-green-400 p-4 rounded-r-md">
                  <p className="text-gray-800">{generatedContent.call_to_action}</p>
                </div>
              </div>

              {/* Hashtags */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Hashtags</h4>
                <div className="flex flex-wrap gap-2">
                  {generatedContent.hashtags.split(' ').map((tag, index) => (
                    <Badge key={index} variant="outline" className="text-blue-600">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Full Post Preview */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Full LinkedIn Post</h4>
                <div className="bg-white border border-gray-200 p-6 rounded-lg">
                  <p className="text-gray-800 whitespace-pre-line">{generatedContent.full_post}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              onClick={() => router.push(`/dashboard/content/${generatedContent.id}`)}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              View & Edit Content
            </Button>
            <Button 
              variant="outline"
              onClick={() => router.push('/dashboard/content')}
            >
              Go to Content Library
            </Button>
            <Button 
              variant="outline"
              onClick={resetForm}
            >
              Generate Another
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <Link 
            href="/dashboard/content" 
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-500 mb-4"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to Content
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Generate New Content</h1>
            <p className="mt-2 text-gray-600">
              Create high-engagement LinkedIn content using our proven €290K algorithms
            </p>
          </div>
        </div>

        {/* Content Generation Form */}
        <ContentGenerationForm onSuccess={handleGenerationSuccess} />
      </div>
    </div>
  )
}