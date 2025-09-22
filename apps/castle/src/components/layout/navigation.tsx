'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  Activity,
  Search,
  Database,
  Settings,
  PlayCircle
} from 'lucide-react'

const navigation = [
  {
    name: 'Dashboard',
    href: '/',
    icon: Activity,
    description: 'System overview and health monitoring'
  },
  {
    name: 'Runs',
    href: '/runs',
    icon: PlayCircle,
    description: 'Task execution and results'
  },
  {
    name: 'Knowledge',
    href: '/knowledge',
    icon: Search,
    description: 'Search and ingest knowledge base'
  },
  {
    name: 'Services',
    href: '/services',
    icon: Database,
    description: 'Service health and monitoring'
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Configuration and API keys'
  }
]

export function Navigation() {
  const pathname = usePathname()

  return (
    <nav className="flex flex-col space-y-1">
      {navigation.map((item) => {
        const isActive = pathname === item.href
        return (
          <Link
            key={item.name}
            href={item.href}
            className={cn(
              'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent'
            )}
          >
            <item.icon
              className={cn(
                'mr-3 h-5 w-5 flex-shrink-0',
                isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-foreground'
              )}
            />
            <span className="flex-1">{item.name}</span>
          </Link>
        )
      })}
    </nav>
  )
}

export function MobileNavigation() {
  const pathname = usePathname()

  return (
    <nav className="flex overflow-x-auto space-x-1 pb-2">
      {navigation.map((item) => {
        const isActive = pathname === item.href
        return (
          <Link
            key={item.name}
            href={item.href}
            className={cn(
              'flex flex-col items-center px-3 py-2 text-xs font-medium rounded-md transition-colors min-w-max',
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent'
            )}
          >
            <item.icon className="h-5 w-5 mb-1" />
            <span>{item.name}</span>
          </Link>
        )
      })}
    </nav>
  )
}