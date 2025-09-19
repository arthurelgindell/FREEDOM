'use client'

import { Navigation } from './navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatDate } from '@/lib/utils'

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  return (
    <aside className={`flex flex-col w-64 border-r bg-background ${className}`}>
      <div className="flex-1 flex flex-col min-h-0">
        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1">
          <Navigation />
        </nav>

        {/* Status footer */}
        <div className="p-4 border-t">
          <Card>
            <CardContent className="p-3">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Status</span>
                  <Badge variant="success" className="text-xs">
                    Operational
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  Last updated: {formatDate(new Date())}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </aside>
  )
}