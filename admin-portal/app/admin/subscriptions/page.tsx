'use client'

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  CreditCard,
  TrendingUp,
  DollarSign,
} from "lucide-react"
import { formatCurrency, formatDate } from "@/lib/utils"

interface Subscription {
  id: string
  tenant: string
  plan: 'PROFESSIONAL' | 'PERFORMANCE' | 'ENTERPRISE'
  status: 'ACTIVE' | 'PAST_DUE' | 'CANCELLED' | 'TRIALING'
  amount: number
  currentPeriodEnd: Date
}

const mockSubscriptions: Subscription[] = [
  {
    id: '1',
    tenant: 'Performance Motors',
    plan: 'ENTERPRISE',
    status: 'ACTIVE',
    amount: 399,
    currentPeriodEnd: new Date('2025-01-31'),
  },
  {
    id: '2',
    tenant: 'Aussie Auto Repairs',
    plan: 'PROFESSIONAL',
    status: 'TRIALING',
    amount: 149,
    currentPeriodEnd: new Date('2025-01-25'),
  },
  {
    id: '3',
    tenant: 'Speed Works',
    plan: 'PERFORMANCE',
    status: 'PAST_DUE',
    amount: 249,
    currentPeriodEnd: new Date('2025-01-14'),
  }
]

const statusColors = {
  ACTIVE: 'bg-green-100 text-green-800',
  PAST_DUE: 'bg-red-100 text-red-800',
  CANCELLED: 'bg-gray-100 text-gray-800',
  TRIALING: 'bg-blue-100 text-blue-800',
}

const planColors = {
  PROFESSIONAL: 'bg-gray-100 text-gray-800',
  PERFORMANCE: 'bg-purple-100 text-purple-800',
  ENTERPRISE: 'bg-blue-100 text-blue-800',
}

export default function SubscriptionsPage() {
  const stats = {
    monthlyRevenue: 78420,
    activeSubscriptions: mockSubscriptions.filter(s => s.status === 'ACTIVE').length,
    churnRate: 1.3,
    avgRevenuePerUser: 2847,
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Subscription Management</h1>
          <p className="text-gray-500">
            Monitor billing, subscriptions, and revenue
          </p>
        </div>
        <Button>
          <CreditCard className="mr-2 h-4 w-4" />
          Billing Settings
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{formatCurrency(stats.monthlyRevenue)}</div>
            <div className="text-sm text-gray-500">Monthly Recurring Revenue</div>
            <div className="text-xs text-green-600 mt-1">+23% from last month</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.activeSubscriptions}</div>
            <div className="text-sm text-gray-500">Active Subscriptions</div>
            <div className="text-xs text-green-600 mt-1">+18% from last month</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.churnRate}%</div>
            <div className="text-sm text-gray-500">Churn Rate</div>
            <div className="text-xs text-green-600 mt-1">-0.3% from last month</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{formatCurrency(stats.avgRevenuePerUser)}</div>
            <div className="text-sm text-gray-500">Avg Revenue Per User</div>
            <div className="text-xs text-green-600 mt-1">+5% from last month</div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="subscriptions" className="space-y-4">
        <TabsList>
          <TabsTrigger value="subscriptions">Subscriptions</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="subscriptions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Active Subscriptions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tenant</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Period End</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockSubscriptions.map((subscription) => (
                      <TableRow key={subscription.id}>
                        <TableCell>
                          <div className="font-medium">{subscription.tenant}</div>
                        </TableCell>
                        <TableCell>
                          <Badge className={planColors[subscription.plan]}>
                            {subscription.plan}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={statusColors[subscription.status]}>
                            {subscription.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="font-medium">
                            {formatCurrency(subscription.amount)}/mo
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {formatDate(subscription.currentPeriodEnd)}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex space-x-2">
                            <Button variant="outline" size="sm">View</Button>
                            <Button variant="outline" size="sm">Edit</Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="billing">
          <Card>
            <CardHeader>
              <CardTitle>Billing Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center text-gray-500">
                Billing history and payment management tools.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          <Card>
            <CardHeader>
              <CardTitle>Revenue Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center text-gray-500">
                Detailed revenue and subscription analytics.
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
