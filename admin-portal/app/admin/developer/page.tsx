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
  Code,
  Key,
  Activity,
  Database,
  Plus,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap
} from "lucide-react"

const statusColors = {
  ACTIVE: 'bg-green-100 text-green-800',
  INACTIVE: 'bg-gray-100 text-gray-800',
  ERROR: 'bg-red-100 text-red-800',
  PENDING: 'bg-yellow-100 text-yellow-800',
}

export default function DeveloperPage() {
  const stats = {
    totalRequests: 3529,
    avgResponseTime: 187,
    avgSuccessRate: 99.2,
    activeIntegrations: 3,
    errorIntegrations: 1,
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Developer Tools</h1>
          <p className="text-gray-500">
            API management, integrations, and system monitoring
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline">
            <Code className="mr-2 h-4 w-4" />
            API Docs
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create API Key
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.totalRequests}</div>
            <div className="text-sm text-gray-500">API Requests (24h)</div>
            <div className="text-xs text-green-600 mt-1">+12% from yesterday</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.avgResponseTime}ms</div>
            <div className="text-sm text-gray-500">Avg Response Time</div>
            <div className="text-xs text-green-600 mt-1">-5ms from yesterday</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.avgSuccessRate}%</div>
            <div className="text-sm text-gray-500">Success Rate</div>
            <div className="text-xs text-green-600 mt-1">Above target</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.activeIntegrations}</div>
            <div className="text-sm text-gray-500">Active Integrations</div>
            <div className="text-xs text-red-600 mt-1">{stats.errorIntegrations} with errors</div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="api-keys" className="space-y-4">
        <TabsList>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="webhooks">Webhooks</TabsTrigger>
        </TabsList>

        <TabsContent value="api-keys" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API Keys</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Tenant</TableHead>
                      <TableHead>Environment</TableHead>
                      <TableHead>Last Used</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell>
                        <div>
                          <div className="font-medium">Production API Key</div>
                          <div className="text-sm text-gray-500 font-mono">
                            ••••••••••••••••••••••••••••••••
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>Performance Motors</TableCell>
                      <TableCell>
                        <Badge className="bg-red-100 text-red-800">
                          PRODUCTION
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <Clock className="mr-1 h-3 w-3" />
                          Today at 10:30 AM
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={statusColors['ACTIVE']}>
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Active
                        </Badge>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="endpoints">
          <Card>
            <CardHeader>
              <CardTitle>API Endpoints</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Endpoint</TableHead>
                      <TableHead>Usage (24h)</TableHead>
                      <TableHead>Avg Response</TableHead>
                      <TableHead>Success Rate</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell>
                        <div className="font-mono text-sm">GET /api/v1/jobs</div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <Activity className="mr-1 h-3 w-3" />
                          1,247
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <Zap className="mr-1 h-3 w-3" />
                          145ms
                        </div>
                      </TableCell>
                      <TableCell>99.8%</TableCell>
                      <TableCell>
                        <Badge className={statusColors['ACTIVE']}>
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Healthy
                        </Badge>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="integrations">
          <Card>
            <CardHeader>
              <CardTitle>System Integrations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 rounded-full bg-green-500" />
                      <div>
                        <div className="font-medium">Capricorn Society EDI</div>
                        <div className="text-sm text-gray-500">
                          Performance Motors
                        </div>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">Configure</Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="webhooks">
          <Card>
            <CardHeader>
              <CardTitle>Webhook Management</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center text-gray-500">
                Webhook configuration and monitoring tools.
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
