"use client"

import { useState, useEffect, useCallback } from 'react'

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[]
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed'
    platform: string
  }>
  prompt(): Promise<void>
}

export interface PWAInstallPrompt {
  isInstallable: boolean
  isInstalled: boolean
  isOffline: boolean
  showInstallPrompt: () => Promise<void>
  dismissInstallPrompt: () => void
}

export function usePWA(): PWAInstallPrompt {
  const [isInstallable, setIsInstallable] = useState(false)
  const [isInstalled, setIsInstalled] = useState(false)
  const [isOffline, setIsOffline] = useState(false)
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null)

  // Check if app is already installed
  useEffect(() => {
    const checkIfInstalled = () => {
      // Check for display mode
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches
      // Check for iOS Safari in standalone mode
      const isIOSStandalone = (window.navigator as any).standalone === true
      
      setIsInstalled(isStandalone || isIOSStandalone)
    }

    checkIfInstalled()

    // Listen for display mode changes
    const mediaQuery = window.matchMedia('(display-mode: standalone)')
    mediaQuery.addEventListener('change', checkIfInstalled)

    return () => mediaQuery.removeEventListener('change', checkIfInstalled)
  }, [])

  // Handle beforeinstallprompt event
  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      console.log('PWA: Install prompt available')
      e.preventDefault()
      setDeferredPrompt(e as BeforeInstallPromptEvent)
      setIsInstallable(true)
    }

    const handleAppInstalled = () => {
      console.log('PWA: App installed')
      setIsInstalled(true)
      setIsInstallable(false)
      setDeferredPrompt(null)
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    window.addEventListener('appinstalled', handleAppInstalled)

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
      window.removeEventListener('appinstalled', handleAppInstalled)
    }
  }, [])

  // Monitor online/offline status
  useEffect(() => {
    const handleOnlineStatus = () => {
      setIsOffline(!navigator.onLine)
    }

    handleOnlineStatus() // Initial check

    window.addEventListener('online', handleOnlineStatus)
    window.addEventListener('offline', handleOnlineStatus)

    return () => {
      window.removeEventListener('online', handleOnlineStatus)
      window.removeEventListener('offline', handleOnlineStatus)
    }
  }, [])

  const showInstallPrompt = useCallback(async () => {
    if (!deferredPrompt) {
      console.log('PWA: No install prompt available')
      return
    }

    try {
      await deferredPrompt.prompt()
      const { outcome } = await deferredPrompt.userChoice
      
      console.log(`PWA: Install prompt ${outcome}`)
      
      if (outcome === 'accepted') {
        setIsInstallable(false)
        setDeferredPrompt(null)
      }
    } catch (error) {
      console.error('PWA: Error showing install prompt:', error)
    }
  }, [deferredPrompt])

  const dismissInstallPrompt = useCallback(() => {
    setIsInstallable(false)
    setDeferredPrompt(null)
  }, [])

  return {
    isInstallable,
    isInstalled,
    isOffline,
    showInstallPrompt,
    dismissInstallPrompt
  }
}

// Service Worker registration hook
export function useServiceWorker() {
  const [isSupported, setIsSupported] = useState(false)
  const [isRegistered, setIsRegistered] = useState(false)
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null)
  const [updateAvailable, setUpdateAvailable] = useState(false)

  useEffect(() => {
    if ('serviceWorker' in navigator) {
      setIsSupported(true)

      // Register service worker
      navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      })
      .then((reg) => {
        console.log('SW: Service Worker registered:', reg.scope)
        setRegistration(reg)
        setIsRegistered(true)

        // Check for updates
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing
          
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                console.log('SW: Update available')
                setUpdateAvailable(true)
              }
            })
          }
        })
      })
      .catch((error) => {
        console.error('SW: Service Worker registration failed:', error)
      })

      // Handle controller change (new SW activated)
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        console.log('SW: New service worker activated')
        window.location.reload()
      })
    }
  }, [])

  const updateServiceWorker = useCallback(() => {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' })
    }
  }, [registration])

  return {
    isSupported,
    isRegistered,
    updateAvailable,
    updateServiceWorker
  }
}

// Push notification hook
export function usePushNotifications() {
  const [isSupported, setIsSupported] = useState(false)
  const [permission, setPermission] = useState<NotificationPermission>('default')
  const [subscription, setSubscription] = useState<PushSubscription | null>(null)

  useEffect(() => {
    if ('Notification' in window && 'serviceWorker' in navigator) {
      setIsSupported(true)
      setPermission(Notification.permission)
    }
  }, [])

  const requestPermission = useCallback(async () => {
    if (!isSupported) {
      throw new Error('Push notifications not supported')
    }

    const permission = await Notification.requestPermission()
    setPermission(permission)
    
    if (permission === 'granted') {
      await subscribeToPush()
    }
    
    return permission
  }, [isSupported])

  const subscribeToPush = useCallback(async () => {
    if (!('serviceWorker' in navigator) || permission !== 'granted') {
      return
    }

    try {
      const registration = await navigator.serviceWorker.ready
      
      // In a real implementation, you would get this from your server
      const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || ''
      
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: vapidPublicKey
      })

      console.log('Push: Subscribed to push notifications')
      setSubscription(subscription)

      // Send subscription to server
      await fetch('/api/v1/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(subscription)
      })

    } catch (error) {
      console.error('Push: Failed to subscribe:', error)
    }
  }, [permission])

  const unsubscribeFromPush = useCallback(async () => {
    if (!subscription) {
      return
    }

    try {
      await subscription.unsubscribe()
      setSubscription(null)
      
      // Remove subscription from server
      await fetch('/api/v1/push/unsubscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(subscription)
      })

    } catch (error) {
      console.error('Push: Failed to unsubscribe:', error)
    }
  }, [subscription])

  return {
    isSupported,
    permission,
    subscription,
    requestPermission,
    subscribeToPush,
    unsubscribeFromPush
  }
}