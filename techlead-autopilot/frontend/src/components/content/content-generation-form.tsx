"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import * as z from "zod"
import { Loader2, Sparkles, Target, Users } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"

import { contentApi, ContentGenerationRequest, ContentGenerated } from "@/lib/api-client"
import { ContentTypeSelector } from "./content-type-selector"

const contentGenerationSchema = z.object({
  content_type: z.string().min(1, "Content type is required"),
  topic: z.string().min(10, "Topic must be at least 10 characters").max(200, "Topic must be less than 200 characters"),
  target_audience: z.string().optional(),
  consultation_focused: z.boolean().optional(),
  target_engagement_rate: z.number().min(0.01).max(0.1).optional(),
})

type ContentGenerationForm = z.infer<typeof contentGenerationSchema>

interface ContentGenerationFormProps {
  onSuccess?: (content: ContentGenerated) => void
  className?: string
}

export function ContentGenerationForm({ onSuccess, className }: ContentGenerationFormProps) {
  const [step, setStep] = useState(1)
  const queryClient = useQueryClient()

  const form = useForm<ContentGenerationForm>({
    resolver: zodResolver(contentGenerationSchema),
    defaultValues: {
      content_type: "",
      topic: "",
      target_audience: "technical_leaders",
      consultation_focused: true,
      target_engagement_rate: 0.035,
    },
  })

  const generateContentMutation = useMutation({
    mutationFn: (data: ContentGenerationRequest) => contentApi.generate(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
      onSuccess?.(data)
    },
  })

  const onSubmit = async (data: ContentGenerationForm) => {
    const requestData: ContentGenerationRequest = {
      content_type: data.content_type,
      topic: data.topic,
      target_audience: data.target_audience || "technical_leaders",
      consultation_focused: data.consultation_focused ?? true,
      target_engagement_rate: data.target_engagement_rate ?? 0.035,
    }

    generateContentMutation.mutate(requestData)
  }

  const watchedTopic = form.watch("topic")
  const watchedContentType = form.watch("content_type")

  const nextStep = async () => {
    if (step === 1) {
      const isValidContentType = await form.trigger("content_type")
      if (isValidContentType) setStep(2)
    } else if (step === 2) {
      const isValidTopic = await form.trigger("topic")
      if (isValidTopic) setStep(3)
    }
  }

  const previousStep = () => {
    if (step > 1) setStep(step - 1)
  }

  return (
    <div className={className}>
      <Card className="w-full max-w-4xl mx-auto">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-blue-600" />
                Generate Technical Content
              </CardTitle>
              <CardDescription>
                Create high-engagement LinkedIn content using proven €290K algorithms
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-xs">
              Step {step} of 3
            </Badge>
          </div>
          <Progress value={(step / 3) * 100} className="mt-4" />
        </CardHeader>

        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              {step === 1 && (
                <div className="space-y-6">
                  <FormField
                    control={form.control}
                    name="content_type"
                    render={({ field }) => (
                      <FormItem>
                        <ContentTypeSelector
                          selectedType={field.value}
                          onSelect={field.onChange}
                        />
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <div className="flex justify-end">
                    <Button 
                      type="button" 
                      onClick={nextStep}
                      disabled={!watchedContentType}
                    >
                      Continue to Topic
                    </Button>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-6">
                  <FormField
                    control={form.control}
                    name="topic"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-base font-semibold">
                          What topic do you want to write about?
                        </FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="e.g., How to scale engineering teams from 5 to 50 developers without losing velocity"
                            className="min-h-[120px] resize-none"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Be specific about the challenge, insight, or story you want to share. 
                          This will be the foundation of your content.
                        </FormDescription>
                        <div className="flex justify-between text-xs text-gray-500">
                          <FormMessage />
                          <span>{watchedTopic?.length || 0}/200</span>
                        </div>
                      </FormItem>
                    )}
                  />

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h4 className="font-medium text-blue-900 mb-2">💡 Pro Tips for Better Content</h4>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>• Include specific numbers or metrics when possible</li>
                      <li>• Reference real challenges your audience faces</li>
                      <li>• Mention tools, frameworks, or methodologies</li>
                      <li>• Share personal experience or lessons learned</li>
                    </ul>
                  </div>

                  <div className="flex justify-between">
                    <Button type="button" variant="outline" onClick={previousStep}>
                      Back
                    </Button>
                    <Button 
                      type="button" 
                      onClick={nextStep}
                      disabled={!watchedTopic || watchedTopic.length < 10}
                    >
                      Configure Settings
                    </Button>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <FormField
                      control={form.control}
                      name="target_audience"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center gap-2">
                            <Users className="h-4 w-4" />
                            Target Audience
                          </FormLabel>
                          <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Select target audience" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="technical_leaders">Technical Leaders</SelectItem>
                              <SelectItem value="startup_founders">Startup Founders</SelectItem>
                              <SelectItem value="engineering_managers">Engineering Managers</SelectItem>
                              <SelectItem value="senior_engineers">Senior Engineers</SelectItem>
                              <SelectItem value="ctos_vp_engineering">CTOs & VP Engineering</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormDescription>
                            Who is the primary audience for this content?
                          </FormDescription>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="target_engagement_rate"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center gap-2">
                            <Target className="h-4 w-4" />
                            Target Engagement Rate
                          </FormLabel>
                          <Select 
                            onValueChange={(value) => field.onChange(parseFloat(value))} 
                            defaultValue={field.value?.toString()}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Select engagement target" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="0.025">Conservative (2.5%)</SelectItem>
                              <SelectItem value="0.035">Optimal (3.5%)</SelectItem>
                              <SelectItem value="0.045">Aggressive (4.5%)</SelectItem>
                              <SelectItem value="0.060">Viral (6.0%)</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormDescription>
                            Higher rates generate more engagement but may be less authentic
                          </FormDescription>
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={form.control}
                    name="consultation_focused"
                    render={({ field }) => (
                      <FormItem>
                        <div className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            id="consultation_focused"
                            checked={field.value}
                            onChange={field.onChange}
                            className="rounded border-gray-300"
                          />
                          <Label htmlFor="consultation_focused" className="text-sm font-medium">
                            Optimize for consultation inquiries
                          </Label>
                        </div>
                        <FormDescription>
                          Includes subtle consultation hooks that increase lead generation by 40%
                        </FormDescription>
                      </FormItem>
                    )}
                  />

                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h4 className="font-medium text-green-900 mb-2">🎯 Content Preview</h4>
                    <div className="text-sm text-green-800 space-y-1">
                      <p><strong>Type:</strong> {watchedContentType?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</p>
                      <p><strong>Topic:</strong> {watchedTopic?.slice(0, 80)}{watchedTopic?.length > 80 ? '...' : ''}</p>
                      <p><strong>Audience:</strong> {form.watch('target_audience')?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</p>
                    </div>
                  </div>

                  <div className="flex justify-between">
                    <Button type="button" variant="outline" onClick={previousStep}>
                      Back
                    </Button>
                    <Button 
                      type="submit" 
                      disabled={generateContentMutation.isPending}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {generateContentMutation.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Sparkles className="mr-2 h-4 w-4" />
                          Generate Content
                        </>
                      )}
                    </Button>
                  </div>

                  {generateContentMutation.error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
                      Failed to generate content. Please try again.
                    </div>
                  )}
                </div>
              )}
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}