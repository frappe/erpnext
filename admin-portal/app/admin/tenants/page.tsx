'use client'

import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Building2,
  Search,
  Filter,
  MoreVertical,
  Users,
  DollarSign,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle
} from "lucide-react"
import { formatCurrency, formatDate } from "@/lib/utils"

interface Tenant {
  id: string
  name: string
  subdomain: string
  status: 'TRIAL' | 'ACTIVE' | 'SUSPENDED' | 'CANCELLED'
  plan: 'PROFESSIONAL' | 'PERFORMANCE' | 'ENTERPRISE'
  userCount: number
  monthlyRevenue: number
  trialEndsAt?: Date
  createdAt: Date
  lastLoginAt?: Date
  primaryContact: {
    firstName: string
    lastName: string
    email: string
  }
}

const mockTenants: Tenant[] = [
  {
    id: '1',
    name: 'Performance Motors',
    subdomain: 'performance-motors',
    status: 'ACTIVE',
    plan: 'ENTERPRISE',
    userCount: 8,
    monthlyRevenue: 399,
    createdAt: new Date('2024-01-15'),
    lastLoginAt: new Date('2025-01-15'),
    primaryContact: {
      firstName: 'John',
      lastName: 'Smith',
      email: 'john@performancemotors.com.au'
    }
  },
  {
    id: '2',
    name: 'Aussie Auto Repairs',
    subdomain: 'aussie-auto',
    status: 'TRIAL',
    plan: 'PROFESSIONAL',
    userCount: 3,
    monthlyRevenue: 0,
    trialEndsAt: new Date('2025-01-25'),
    createdAt: new Date('2025-01-10'),
    lastLoginAt: new Date('2025-01-14'),
    primaryContact: {
      firstName: 'Sarah',
      lastName: 'Johnson',
      email: 'sarah@aussieauto.com.au'
    }
  },
  {
    id: '3',
    name: 'Speed Works',
    subdomain: 'speed-works',
    status: 'SUSPENDED',
    plan: 'PERFORMANCE',
    userCount: 5,
    monthlyRevenue: 249,
    createdAt: new Date('2024-03-20'),
    lastLoginAt: new Date('2025-01-10'),
    primaryContact: {
      firstName: 'Mike',
      lastName: 'Wilson',
      email: 'mike@speedworks.co.nz'
    }
  }
]

const statusIcons = {
  ACTIVE: CheckCircle,
  TRIAL: Clock,
  SUSPENDED: AlertTriangle,
  CANCELLED: XCircle,
}

const statusColors = {
  ACTIVE: 'bg-green-100 text-green-800',
  TRIAL: 'bg-blue-100 text-blue-800',
  SUSPENDED: 'bg-orange-100 text-orange-800',
  CANCELLED: 'bg-red-100 text-red-800',
}

const planColors = {
  PROFESSIONAL: 'bg-gray-100 text-gray-800',
  PERFORMANCE: 'bg-purple-100 text-purple-800',
  ENTERPRISE: 'bg-blue-100 text-blue-800',
}

export default function TenantsPage() {
  const [searchTerm, setSearchTerm] = React.useState('')
  const [statusFilter, setStatusFilter] = React.useState<string>('all')

  const filteredTenants = mockTenants.filter(tenant => {
    const matchesSearch = tenant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         tenant.subdomain.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         tenant.primaryContact.email.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesStatus = statusFilter === 'all' || tenant.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const getTenantStats = () => {
    return {
      total: mockTenants.length,
      active: mockTenants.filter(t => t.status === 'ACTIVE').length,
      trial: mockTenants.filter(t => t.status === 'TRIAL').length,
      suspended: mockTenants.filter(t => t.status === 'SUSPENDED').length,
      totalRevenue: mockTenants.reduce((sum, t) => sum + t.monthlyRevenue, 0)
    }
  }

  const stats = getTenantStats()

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Tenant Management</h1>
          <p className="text-gray-500">
            Manage customer accounts and subscriptions
          </p>
        </div>
        <Button>
          <Building2 className="mr-2 h-4 w-4" />
          Add Tenant
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-500">Total Tenants</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-600">{stats.active}</div>
            <div className="text-sm text-gray-500">Active</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-600">{stats.trial}</div>
            <div className="text-sm text-gray-500">Trial</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-orange-600">{stats.suspended}</div>
            <div className="text-sm text-gray-500">Suspended</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{formatCurrency(stats.totalRevenue)}</div>
            <div className="text-sm text-gray-500">Monthly Revenue</div>
          </CardContent>
        </Card>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Tenants</CardTitle>
            <div className="flex items-center space-x-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search tenants..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-80"
                />
              </div>
              <Button variant="outline">
                <Filter className="mr-2 h-4 w-4" />
                Filters
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tenant</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Users</TableHead>
                  <TableHead>Revenue</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTenants.map((tenant) => {
                  const StatusIcon = statusIcons[tenant.status]
                  return (
                    <TableRow key={tenant.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{tenant.name}</div>
                          <div className="text-sm text-gray-500">
                            {tenant.subdomain}.autocrm.com.au
                          </div>
                          <div className="text-sm text-gray-500">
                            {tenant.primaryContact.firstName} {tenant.primaryContact.lastName}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={statusColors[tenant.status]}>
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {tenant.status}
                        </Badge>
                        {tenant.status === 'TRIAL' && tenant.trialEndsAt && (
                          <div className="text-xs text-gray-500 mt-1">
                            Ends: {formatDate(tenant.trialEndsAt)}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge className={planColors[tenant.plan]}>
                          {tenant.plan}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <Users className="mr-1 h-3 w-3" />
                          {tenant.userCount}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <DollarSign className="mr-1 h-3 w-3" />
                          {formatCurrency(tenant.monthlyRevenue)}/mo
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <Calendar className="mr-1 h-3 w-3" />
                          {formatDate(tenant.createdAt)}
                        </div>
                      </TableCell>
                      <TableCell>
                        {tenant.lastLoginAt ? (
                          <div className="text-sm">
                            {formatDate(tenant.lastLoginAt)}
                          </div>
                        ) : (
                          <span className="text-gray-500">Never</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="h-8 w-8 p-0">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem>View Details</DropdownMenuItem>
                            <DropdownMenuItem>Edit Tenant</DropdownMenuItem>
                            <DropdownMenuItem>Manage Users</DropdownMenuItem>
                            <DropdownMenuItem>Billing History</DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem>Suspend Account</DropdownMenuItem>
                            <DropdownMenuItem className="text-red-600">
                              Delete Tenant
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
