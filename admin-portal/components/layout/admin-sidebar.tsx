"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  Users,
  Building2,
  CreditCard,
  HeadphonesIcon,
  Settings,
  BarChart3,
  Mail,
  Code,
  Megaphone,
  Shield,
  Database,
  Bell,
  Flag
} from "lucide-react"

const navigation = [
  {
    name: "Dashboard",
    href: "/admin",
    icon: LayoutDashboard,
    description: "Overview & metrics"
  },
  {
    name: "Tenant Management",
    href: "/admin/tenants",
    icon: Building2,
    description: "Manage customers"
  },
  {
    name: "User Management",
    href: "/admin/users",
    icon: Users,
    description: "Admin users & permissions"
  },
  {
    name: "Subscriptions",
    href: "/admin/subscriptions",
    icon: CreditCard,
    description: "Billing & plans"
  },
  {
    name: "Support Center",
    href: "/admin/support",
    icon: HeadphonesIcon,
    description: "Help desk & tickets"
  },
  {
    name: "Analytics",
    href: "/admin/analytics",
    icon: BarChart3,
    description: "Usage & performance"
  },
  {
    name: "Communications",
    href: "/admin/communications",
    icon: Mail,
    description: "Email & notifications"
  },
  {
    name: "Marketing Tools",
    href: "/admin/marketing",
    icon: Megaphone,
    description: "Campaigns & content"
  },
  {
    name: "Developer Tools",
    href: "/admin/developer",
    icon: Code,
    description: "API & integrations"
  },
  {
    name: "Feature Flags",
    href: "/admin/features",
    icon: Flag,
    description: "Feature rollouts"
  },
  {
    name: "System Config",
    href: "/admin/system",
    icon: Database,
    description: "System settings"
  },
  {
    name: "Security",
    href: "/admin/security",
    icon: Shield,
    description: "Audit & compliance"
  },
  {
    name: "Notifications",
    href: "/admin/notifications",
    icon: Bell,
    description: "Alert center"
  },
  {
    name: "Settings",
    href: "/admin/settings",
    icon: Settings,
    description: "Admin preferences"
  },
]

export function AdminSidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full w-72 flex-col bg-gray-900">
      <div className="flex h-16 items-center px-6">
        <div className="flex items-center space-x-2">
          <Shield className="h-8 w-8 text-blue-400" />
          <div>
            <span className="text-xl font-bold text-white">AutoCRM Admin</span>
            <div className="text-xs text-gray-400">Management Portal</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-4 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group flex items-center rounded-md px-3 py-3 text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-700 hover:text-white"
              )}
            >
              <item.icon
                className={cn(
                  "mr-3 h-5 w-5 flex-shrink-0",
                  isActive ? "text-white" : "text-gray-400 group-hover:text-white"
                )}
              />
              <div className="flex-1 min-w-0">
                <div className="truncate">{item.name}</div>
                <div className="text-xs text-gray-400 truncate">{item.description}</div>
              </div>
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-gray-700">
        <div className="text-xs text-gray-400">
          AutoCRM Pro Admin Portal v1.0.0
        </div>
      </div>
    </div>
  )
}
