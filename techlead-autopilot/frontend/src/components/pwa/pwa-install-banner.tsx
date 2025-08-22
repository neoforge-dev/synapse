"use client"

import { useState, useEffect } from 'react'
import { X, Download, Smartphone, Monitor } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

import { usePWA } from '@/hooks/use-pwa'

export function PWAInstallBanner() {
  const { isInstallable, isInstalled, showInstallPrompt } = usePWA()
  const [isDismissed, setIsDismissed] = useState(false)
  const [showBanner, setShowBanner] = useState(false)

  // Check if banner was previously dismissed
  useEffect(() => {
    const dismissed = localStorage.getItem('pwa-install-dismissed')
    const dismissedDate = dismissed ? new Date(dismissed) : null
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
    
    // Show banner again after 24 hours
    if (!dismissedDate || dismissedDate < oneDayAgo) {
      setIsDismissed(false)
    } else {
      setIsDismissed(true)
    }
  }, [])

  // Show banner with delay for better UX
  useEffect(() => {
    if (isInstallable && !isDismissed && !isInstalled) {
      const timer = setTimeout(() => {
        setShowBanner(true)
      }, 3000) // Show after 3 seconds

      return () => clearTimeout(timer)
    }
  }, [isInstallable, isDismissed, isInstalled])

  const handleInstall = async () => {
    try {
      await showInstallPrompt()
      setShowBanner(false)
    } catch (error) {
      console.error('PWA Install Error:', error)
    }
  }

  const handleDismiss = () => {
    setShowBanner(false)
    setIsDismissed(true)
    localStorage.setItem('pwa-install-dismissed', new Date().toISOString())
  }

  if (!showBanner || isInstalled) {
    return null
  }

  return (
    <>
      {/* Mobile Banner */}
      <div className="fixed bottom-0 left-0 right-0 z-50 p-4 md:hidden">
        <Card className="border-blue-200 bg-blue-50 shadow-lg">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-full">
                <Smartphone className="h-5 w-5 text-blue-600" />
              </div>
              
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-blue-900 text-sm">
                  Install TechLead AutoPilot
                </h3>
                <p className="text-xs text-blue-700 mt-1">
                  Get the app for quick content approval & lead management
                </p>
              </div>
              
              <div className="flex items-center gap-2">
                <Button
                  onClick={handleInstall}
                  size="sm"
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Install
                </Button>
                <Button
                  onClick={handleDismiss}
                  variant="ghost"
                  size="sm"
                  className="text-blue-600 p-2"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Desktop Banner */}
      <div className="fixed top-20 right-4 z-50 max-w-sm hidden md:block">
        <Card className="border-blue-200 bg-white shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-blue-100 rounded-full">
                  <Monitor className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Install App</h3>
                  <Badge variant="secondary" className="text-xs mt-1">
                    Recommended
                  </Badge>
                </div>
              </div>
              <Button
                onClick={handleDismiss}
                variant="ghost"
                size="sm"
                className="text-gray-400 hover:text-gray-600 -mt-2 -mr-2 p-2"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <p className="text-sm text-gray-600 mb-4 leading-relaxed">
              Install TechLead AutoPilot for faster access, offline support, and native desktop experience.
            </p>

            <div className="space-y-2 mb-4">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <div className="w-1 h-1 bg-green-500 rounded-full"></div>
                <span>Works offline</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <div className="w-1 h-1 bg-green-500 rounded-full"></div>
                <span>Push notifications for urgent leads</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <div className="w-1 h-1 bg-green-500 rounded-full"></div>
                <span>Native app-like experience</span>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={handleInstall}
                size="sm"
                className="flex-1 bg-blue-600 hover:bg-blue-700"
              >
                <Download className="mr-2 h-4 w-4" />
                Install App
              </Button>
              <Button
                onClick={handleDismiss}
                variant="outline"
                size="sm"
              >
                Later
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}

// Install prompt in app settings or dashboard
export function PWAInstallButton() {
  const { isInstallable, isInstalled, showInstallPrompt } = usePWA()

  const handleInstall = async () => {
    try {
      await showInstallPrompt()
    } catch (error) {
      console.error('PWA Install Error:', error)
    }
  }

  if (!isInstallable || isInstalled) {
    return null
  }

  return (
    <Button
      onClick={handleInstall}
      variant="outline"
      className="w-full"
    >
      <Download className="mr-2 h-4 w-4" />
      Install App
    </Button>
  )
}

// Offline indicator
export function OfflineIndicator() {
  const { isOffline } = usePWA()

  if (!isOffline) {
    return null
  }

  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50">
      <div className="bg-orange-100 border border-orange-200 text-orange-800 px-3 py-1 rounded-full text-sm font-medium">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
          Working offline
        </div>
      </div>
    </div>
  )
}