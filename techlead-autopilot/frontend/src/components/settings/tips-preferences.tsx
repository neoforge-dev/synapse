"use client"

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { useContextualTips } from '@/components/onboarding/contextual-tips'
import { cn } from '@/lib/utils'
import {
  Lightbulb,
  RotateCcw,
  Bug,
  Info,
  CheckCircle,
  AlertCircle
} from 'lucide-react'

interface TipsPreferencesProps {
  className?: string
}

export function TipsPreferences({ className }: TipsPreferencesProps) {
  const { 
    isEnabled, 
    showDebugInfo, 
    toggleTips, 
    toggleDebugMode, 
    clearDismissedTips 
  } = useContextualTips()

  const getTipStats = () => {
    const dismissed = JSON.parse(localStorage.getItem('techlead-dismissed-tips') || '[]')
    const seen = JSON.parse(localStorage.getItem('techlead-tips-seen') || '[]')
    const actions = JSON.parse(localStorage.getItem('techlead-tip-actions') || '[]')
    
    return {
      dismissed: dismissed.length,
      seen: seen.length,
      actions: actions.length
    }
  }

  const stats = getTipStats()

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          <span>Contextual Tips</span>
        </CardTitle>
        <p className="text-sm text-gray-600">
          Manage helpful tips and guidance throughout the platform
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Main Toggle */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Label htmlFor="tips-enabled" className="text-sm font-medium">
              Enable Contextual Tips
            </Label>
            <p className="text-xs text-gray-500">
              Show helpful tips and guidance as you use the platform
            </p>
          </div>
          <Switch
            id="tips-enabled"
            checked={isEnabled}
            onCheckedChange={toggleTips}
          />
        </div>

        {/* Statistics */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Tip Activity</h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-lg font-semibold text-green-600">{stats.seen}</div>
              <div className="text-xs text-gray-500">Tips Seen</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-blue-600">{stats.dismissed}</div>
              <div className="text-xs text-gray-500">Dismissed</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-purple-600">{stats.actions}</div>
              <div className="text-xs text-gray-500">Actions</div>
            </div>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            {isEnabled ? (
              <>
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span className="text-sm text-green-700">Tips are active</span>
                <Badge variant="default" className="text-xs">
                  Learning your patterns
                </Badge>
              </>
            ) : (
              <>
                <AlertCircle className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-500">Tips are disabled</span>
              </>
            )}
          </div>
        </div>

        {/* Tip Categories */}
        {isEnabled && (
          <div className="space-y-2">
            <Label className="text-sm font-medium">Active Tip Categories</Label>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="text-xs">
                Navigation
              </Badge>
              <Badge variant="outline" className="text-xs">
                Features
              </Badge>
              <Badge variant="outline" className="text-xs">
                Workflows
              </Badge>
              <Badge variant="outline" className="text-xs">
                Optimization
              </Badge>
            </div>
          </div>
        )}

        {/* Management Actions */}
        <div className="pt-4 border-t border-gray-200 space-y-3">
          <h4 className="text-sm font-medium text-gray-900">Management</h4>
          
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={clearDismissedTips}
              disabled={stats.dismissed === 0}
              className="flex items-center space-x-1"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset Dismissed Tips</span>
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleDebugMode}
              className="flex items-center space-x-1"
            >
              <Bug className="w-3 h-3" />
              <span>{showDebugInfo ? 'Hide' : 'Show'} Debug Info</span>
            </Button>
          </div>

          {showDebugInfo && (
            <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-start space-x-2">
                <Info className="w-4 h-4 text-yellow-600 mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-yellow-800">Debug Mode Active</div>
                  <div className="text-xs text-yellow-700 mt-1">
                    Tips will show additional debug information including targeting selectors and timing data.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Privacy Note */}
        <div className="pt-4 border-t border-gray-200">
          <div className="flex items-start space-x-2">
            <Info className="w-4 h-4 text-blue-500 mt-0.5" />
            <div className="text-xs text-gray-600">
              <div className="font-medium mb-1">Privacy Note</div>
              <div>
                Tip activity is stored locally in your browser to personalize your experience. 
                No data is sent to our servers.
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}