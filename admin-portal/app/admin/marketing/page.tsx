'use client'

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Megaphone,
  Plus,
  Send,
} from "lucide-react"
import { formatCurrency } from "@/lib/utils"

export default function MarketingPage() {
  const stats = {
    totalCampaigns: 12,
    activeCampaigns: 3,
    openRate: 32.5,
    clickRate: 8.2,
    totalRevenue: 15420,
    activeAnnouncements: 2
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Marketing Tools</h1>
          <p className="text-gray-500">
            Manage campaigns, announcements, and customer communications
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline">
            <Plus className="mr-2 h-4 w-4" />
            New Announcement
          </Button>
          <Button>
            <Send className="mr-2 h-4 w-4" />
            New Campaign
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.totalCampaigns}</div>
            <div className="text-sm text-gray-500">Total Campaigns</div>
            <div className="text-xs text-green-600 mt-1">{stats.activeCampaigns} active</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.openRate}%</div>
            <div className="text-sm text-gray-500">Average Open Rate</div>
            <div className="text-xs text-green-600 mt-1">Above industry avg</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.clickRate}%</div>
            <div className="text-sm text-gray-500">Click Through Rate</div>
            <div className="text-xs text-green-600 mt-1">+2.3% vs last month</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{formatCurrency(stats.totalRevenue)}</div>
            <div className="text-sm text-gray-500">Campaign Revenue</div>
            <div className="text-xs text-green-600 mt-1">This month</div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="campaigns" className="space-y-4">
        <TabsList>
          <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
          <TabsTrigger value="announcements">Announcements</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="campaigns">
          <Card>
            <CardHeader>
              <CardTitle>Marketing Campaigns</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center text-gray-500">
                Campaign management tools and performance tracking.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="announcements">
          <Card>
            <CardHeader>
              <CardTitle>System Announcements</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-medium">New Capricorn Society Integration</h3>
                      <p className="text-sm text-gray-500 mt-1">
                        Full integration with Capricorn EDI system now available
                      </p>
                    </div>
                    <Badge className="bg-blue-100 text-blue-800">Active</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          <Card>
            <CardHeader>
              <CardTitle>Marketing Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center text-gray-500">
                Detailed marketing and campaign performance analytics.
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
