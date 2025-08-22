// TechLead AutoPilot Service Worker
// Provides offline functionality and caching for PWA

const CACHE_NAME = 'techlead-autopilot-v1.0.0'
const RUNTIME_CACHE = 'runtime-cache-v1'

// Files to cache immediately on service worker install
const PRECACHE_URLS = [
  '/',
  '/dashboard',
  '/dashboard/content',
  '/dashboard/leads',
  '/dashboard/analytics',
  '/offline.html',
  '/manifest.json'
]

// API endpoints to cache with network-first strategy
const API_CACHE_PATTERNS = [
  '/api/v1/content',
  '/api/v1/leads', 
  '/api/v1/analytics'
]

// Install event - precache essential resources
self.addEventListener('install', (event) => {
  console.log('TechLead AutoPilot SW: Installing service worker')
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('TechLead AutoPilot SW: Precaching resources')
        return cache.addAll(PRECACHE_URLS)
      })
      .then(() => {
        // Skip waiting to activate immediately
        return self.skipWaiting()
      })
  )
})

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('TechLead AutoPilot SW: Activating service worker')
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
            console.log('TechLead AutoPilot SW: Deleting old cache:', cacheName)
            return caches.delete(cacheName)
          }
        })
      )
    }).then(() => {
      // Take control of all clients immediately
      return self.clients.claim()
    })
  )
})

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return
  }

  // Skip chrome-extension and other non-http requests
  if (!url.protocol.startsWith('http')) {
    return
  }

  // Handle API requests with network-first strategy
  if (isApiRequest(request)) {
    event.respondWith(
      networkFirst(request)
        .catch(() => {
          // If network fails, try to serve cached version
          return caches.match(request)
            .then(response => response || createOfflineResponse())
        })
    )
    return
  }

  // Handle navigation requests with network-first, fallback to offline page
  if (request.mode === 'navigate') {
    event.respondWith(
      networkFirst(request)
        .catch(() => {
          return caches.match('/offline.html') || 
                 createOfflineResponse('Page not available offline')
        })
    )
    return
  }

  // Handle static assets with cache-first strategy
  if (isStaticAsset(request)) {
    event.respondWith(
      cacheFirst(request)
    )
    return
  }

  // Default: network-first for everything else
  event.respondWith(
    networkFirst(request)
      .catch(() => caches.match(request))
  )
})

// Handle background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('TechLead AutoPilot SW: Background sync triggered:', event.tag)
  
  if (event.tag === 'content-approval') {
    event.waitUntil(syncContentApprovals())
  }
  
  if (event.tag === 'lead-updates') {
    event.waitUntil(syncLeadUpdates())
  }
})

// Handle push notifications for high-priority leads
self.addEventListener('push', (event) => {
  console.log('TechLead AutoPilot SW: Push notification received')
  
  if (!event.data) {
    return
  }

  const data = event.data.json()
  const options = {
    body: data.body,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    data: data.data,
    actions: [
      {
        action: 'view',
        title: 'View Lead',
        icon: '/icons/action-view.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/icons/action-dismiss.png'
      }
    ],
    requireInteraction: data.priority === 'high',
    silent: false,
    timestamp: Date.now(),
    tag: data.tag || 'general'
  }

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  )
})

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('TechLead AutoPilot SW: Notification clicked:', event.action)
  
  event.notification.close()

  if (event.action === 'view' && event.notification.data?.leadId) {
    // Open lead detail page
    event.waitUntil(
      clients.openWindow(`/dashboard/leads/${event.notification.data.leadId}`)
    )
  } else if (event.action !== 'dismiss') {
    // Default action - open dashboard
    event.waitUntil(
      clients.openWindow('/dashboard')
    )
  }
})

// Utility functions

function isApiRequest(request) {
  const url = new URL(request.url)
  return API_CACHE_PATTERNS.some(pattern => url.pathname.startsWith(pattern))
}

function isStaticAsset(request) {
  const url = new URL(request.url)
  return /\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/i.test(url.pathname)
}

async function networkFirst(request) {
  try {
    const response = await fetch(request)
    
    // Cache successful responses
    if (response.status === 200) {
      const cache = await caches.open(RUNTIME_CACHE)
      cache.put(request, response.clone())
    }
    
    return response
  } catch (error) {
    console.log('TechLead AutoPilot SW: Network request failed:', error)
    throw error
  }
}

async function cacheFirst(request) {
  const cachedResponse = await caches.match(request)
  
  if (cachedResponse) {
    // Update cache in background
    fetch(request).then(response => {
      if (response.status === 200) {
        const cache = caches.open(RUNTIME_CACHE)
        cache.then(c => c.put(request, response))
      }
    }).catch(() => {
      // Ignore network errors for background updates
    })
    
    return cachedResponse
  }

  // Not in cache, fetch from network
  const response = await fetch(request)
  
  if (response.status === 200) {
    const cache = await caches.open(RUNTIME_CACHE)
    cache.put(request, response.clone())
  }
  
  return response
}

function createOfflineResponse(message = 'Content not available offline') {
  return new Response(
    JSON.stringify({ 
      error: 'offline',
      message: message,
      timestamp: Date.now()
    }),
    {
      headers: { 'Content-Type': 'application/json' },
      status: 503,
      statusText: 'Service Unavailable'
    }
  )
}

async function syncContentApprovals() {
  console.log('TechLead AutoPilot SW: Syncing content approvals')
  
  // Get pending approvals from IndexedDB
  const pendingApprovals = await getPendingApprovals()
  
  for (const approval of pendingApprovals) {
    try {
      const response = await fetch(`/api/v1/content/${approval.contentId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${approval.token}`
        },
        body: JSON.stringify(approval.data)
      })
      
      if (response.ok) {
        await removePendingApproval(approval.id)
        console.log('TechLead AutoPilot SW: Content approval synced:', approval.contentId)
      }
    } catch (error) {
      console.log('TechLead AutoPilot SW: Failed to sync content approval:', error)
    }
  }
}

async function syncLeadUpdates() {
  console.log('TechLead AutoPilot SW: Syncing lead updates')
  
  // Get pending lead updates from IndexedDB
  const pendingUpdates = await getPendingLeadUpdates()
  
  for (const update of pendingUpdates) {
    try {
      const response = await fetch(`/api/v1/leads/${update.leadId}/follow-up`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${update.token}`
        },
        body: JSON.stringify(update.data)
      })
      
      if (response.ok) {
        await removePendingLeadUpdate(update.id)
        console.log('TechLead AutoPilot SW: Lead update synced:', update.leadId)
      }
    } catch (error) {
      console.log('TechLead AutoPilot SW: Failed to sync lead update:', error)
    }
  }
}

// IndexedDB helpers for offline storage (simplified implementation)
async function getPendingApprovals() {
  // In a real implementation, this would use IndexedDB
  return []
}

async function removePendingApproval(id) {
  // In a real implementation, this would remove from IndexedDB
  console.log('Removing pending approval:', id)
}

async function getPendingLeadUpdates() {
  // In a real implementation, this would use IndexedDB
  return []
}

async function removePendingLeadUpdate(id) {
  // In a real implementation, this would remove from IndexedDB
  console.log('Removing pending lead update:', id)
}