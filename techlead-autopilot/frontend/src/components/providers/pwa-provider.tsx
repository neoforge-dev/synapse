"use client"

import { createContext, useContext, useEffect, useState } from 'react'
import { PushNotificationManager } from '@/lib/push-notifications'

interface PWAContextType {
  isInitialized: boolean
  isInstallable: boolean
  isInstalled: boolean
  isOnline: boolean
  hasNotificationPermission: boolean
  initializePWA: () => Promise<void>
  requestNotificationPermission: () => Promise<void>
}

const PWAContext = createContext<PWAContextType | undefined>(undefined)

export function PWAProvider({ children }: { children: React.ReactNode }) {
  const [isInitialized, setIsInitialized] = useState(false)
  const [isInstallable, setIsInstallable] = useState(false)
  const [isInstalled, setIsInstalled] = useState(false)
  const [isOnline, setIsOnline] = useState(true)
  const [hasNotificationPermission, setHasNotificationPermission] = useState(false)

  useEffect(() => {
    initializePWA()
  }, [])

  const initializePWA = async () => {
    if (typeof window === 'undefined') return

    try {
      // Register service worker
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.register('/sw.js')
        console.log('Service Worker registered:', registration.scope)

        // Listen for install prompt
        window.addEventListener('beforeinstallprompt', (e) => {
          e.preventDefault()
          setIsInstallable(true)
        })

        // Check if already installed
        window.addEventListener('appinstalled', () => {
          setIsInstalled(true)
          setIsInstallable(false)
        })

        // Check display mode
        const mediaQuery = window.matchMedia('(display-mode: standalone)')
        setIsInstalled(mediaQuery.matches || (navigator as any).standalone === true)
        mediaQuery.addEventListener('change', (e) => setIsInstalled(e.matches))
      }

      // Initialize push notifications
      const pushManager = PushNotificationManager.getInstance()
      const initialized = await pushManager.initialize()
      
      if (initialized) {
        setHasNotificationPermission(pushManager.getPermission() === 'granted')
      }

      // Monitor online status
      setIsOnline(navigator.onLine)
      window.addEventListener('online', () => setIsOnline(true))
      window.addEventListener('offline', () => setIsOnline(false))

      setIsInitialized(true)
    } catch (error) {
      console.error('PWA initialization failed:', error)
    }
  }

  const requestNotificationPermission = async () => {
    try {
      const pushManager = PushNotificationManager.getInstance()
      const permission = await pushManager.requestPermission()
      setHasNotificationPermission(permission === 'granted')
    } catch (error) {
      console.error('Failed to request notification permission:', error)
    }
  }

  return (
    <PWAContext.Provider
      value={{
        isInitialized,
        isInstallable,
        isInstalled,
        isOnline,
        hasNotificationPermission,
        initializePWA,
        requestNotificationPermission
      }}
    >
      {children}
    </PWAContext.Provider>
  )
}

export function usePWAContext() {
  const context = useContext(PWAContext)
  if (!context) {
    throw new Error('usePWAContext must be used within a PWAProvider')
  }
  return context
}