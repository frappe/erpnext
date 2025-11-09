'use client'

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Building2,
  Users,
  DollarSign,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap
} from "lucide-react"
import { formatCurrency } from "@/lib/utils"

const mockAdminData = {
  totalTenants: 52,
  activeTenants: 47,
  trialTenants: 8,
  monthlyRevenue: 78420,
  churnRate: 1.3,
  supportTickets: 12,
  systemHealth: 99.2
}

export default function AdminDashboardPage() {
  const cards = [
    {
      title: "Total Tenants",
      value: mockAdminData.totalTenants,
      icon: Building2,
      description: `${mockAdminData.activeTenants} active, ${mockAdminData.trialTenants} trial`,
      trend: "+18% from last month",
      trendColor: "text-green-600"
    },
    {
      title: "Monthly Revenue",
      value: formatCurrency(mockAdminData.monthlyRevenue),
      icon: DollarSign,
      description: "Recurring revenue",
      trend: "+23% from last month",
      trendColor: "text-green-600"
    },
    {
      title: "Active Support Tickets",
      value: mockAdminData.supportTickets,
      icon: AlertCircle,
      description: "Requiring attention",
      trend: mockAdminData.supportTickets > 10 ? "Above normal" : "Normal",
      trendColor: mockAdminData.supportTickets > 10 ? "text-orange-600" : "text-green-600"
    },
    {
      title: "System Health",
      value: `${mockAdminData.systemHealth}%`,
      icon: mockAdminData.systemHealth > 95 ? CheckCircle : AlertCircle,
      description: "Overall system status",
      trend: "All systems operational",
      trendColor: mockAdminData.systemHealth > 95 ? "text-green-600" : "text-orange-600"
    },
    {
      title: "Churn Rate",
      value: `${mockAdminData.churnRate}%`,
      icon: TrendingUp,
      description: "Monthly churn rate",
      trend: mockAdminData.churnRate < 5 ? "Below target" : "Above target",
      trendColor: mockAdminData.churnRate < 5 ? "text-green-600" : "text-red-600"
    },
    {
      title: "API Usage",
      value: "847K",
      icon: Zap,
      description: "Requests this month",
      trend: "+15% from last month",
      trendColor: "text-green-600"
    }
  ]

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-gray-500">
            AutoCRM Pro Application Management Overview
          </p>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {cards.map((card, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {card.title}
              </CardTitle>
              <card.icon className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{card.value}</div>
              <p className="text-xs text-gray-500">
                {card.description}
              </p>
              <p className={`text-xs mt-1 ${card.trendColor}`}>
                {card.trend}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Stats */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Tenant Activity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="font-medium">Performance Motors</div>
                <div className="text-sm text-gray-500">Upgraded to Enterprise</div>
              </div>
              <div className="text-sm text-green-600">+$299/mo</div>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="font-medium">Aussie Auto Repairs</div>
                <div className="text-sm text-gray-500">New trial started</div>
              </div>
              <div className="text-sm text-blue-600">Trial</div>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="font-medium">Speed Works</div>
                <div className="text-sm text-gray-500">Payment overdue</div>
              </div>
              <div className="text-sm text-red-600">Overdue</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Support Queue</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="font-medium">Capricorn Integration Issue</div>
                <div className="text-sm text-gray-500">High Priority</div>
              </div>
              <div className="text-sm text-red-600">Open</div>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="font-medium">ECU Management Question</div>
                <div className="text-sm text-gray-500">Medium Priority</div>
              </div>
              <div className="text-sm text-orange-600">In Progress</div>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="font-medium">Feature Request</div>
                <div className="text-sm text-gray-500">Low Priority</div>
              </div>
              <div className="text-sm text-blue-600">New</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">System Alerts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start space-x-3 p-3 border rounded-lg">
              <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
              <div>
                <div className="font-medium">Database Backup</div>
                <div className="text-sm text-gray-500">Completed successfully</div>
              </div>
            </div>
            <div className="flex items-start space-x-3 p-3 border rounded-lg">
              <Clock className="h-5 w-5 text-blue-600 mt-0.5" />
              <div>
                <div className="font-medium">Scheduled Maintenance</div>
                <div className="text-sm text-gray-500">Tonight at 2:00 AM</div>
              </div>
            </div>
            <div className="flex items-start space-x-3 p-3 border rounded-lg">
              <Zap className="h-5 w-5 text-green-600 mt-0.5" />
              <div>
                <div className="font-medium">API Performance</div>
                <div className="text-sm text-gray-500">99.8% uptime this month</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
