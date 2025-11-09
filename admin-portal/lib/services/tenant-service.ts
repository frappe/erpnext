export interface CreateTenantRequest {
  name: string
  subdomain: string
  customDomain?: string
  plan: 'PROFESSIONAL' | 'PERFORMANCE' | 'ENTERPRISE'
  primaryContact: {
    firstName: string
    lastName: string
    email: string
    phone: string
    position: string
  }
  businessDetails: {
    abn?: string
    address: string
    city: string
    state: string
    postcode: string
    country: string
    industry: string
    businessType: 'SOLE_TRADER' | 'PARTNERSHIP' | 'PTY_LTD' | 'COMPANY'
    yearEstablished?: number
    employeeCount?: number
    website?: string
  }
  trialDays?: number
}

export interface UpdateTenantRequest {
  name?: string
  customDomain?: string
  maxUsers?: number
  maxWorkshops?: number
  businessDetails?: Partial<CreateTenantRequest['businessDetails']>
  primaryContact?: Partial<CreateTenantRequest['primaryContact']>
}

export class TenantService {
  static async createTenant(data: CreateTenantRequest) {
    try {
      const response = await fetch('/api/admin/tenants', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error('Failed to create tenant')
      }

      return response.json()
    } catch (error) {
      console.error('Error creating tenant:', error)
      throw error
    }
  }

  static async updateTenant(tenantId: string, data: UpdateTenantRequest) {
    try {
      const response = await fetch(`/api/admin/tenants/${tenantId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error('Failed to update tenant')
      }

      return response.json()
    } catch (error) {
      console.error('Error updating tenant:', error)
      throw error
    }
  }

  static async suspendTenant(tenantId: string, reason: string) {
    try {
      const response = await fetch(`/api/admin/tenants/${tenantId}/suspend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      })

      if (!response.ok) {
        throw new Error('Failed to suspend tenant')
      }

      return response.json()
    } catch (error) {
      console.error('Error suspending tenant:', error)
      throw error
    }
  }

  static async activateTenant(tenantId: string) {
    try {
      const response = await fetch(`/api/admin/tenants/${tenantId}/activate`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error('Failed to activate tenant')
      }

      return response.json()
    } catch (error) {
      console.error('Error activating tenant:', error)
      throw error
    }
  }

  static async deleteTenant(tenantId: string) {
    try {
      const response = await fetch(`/api/admin/tenants/${tenantId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error('Failed to delete tenant')
      }

      return response.json()
    } catch (error) {
      console.error('Error deleting tenant:', error)
      throw error
    }
  }

  static async getTenantUsage(tenantId: string, dateRange: { start: Date; end: Date }) {
    try {
      const params = new URLSearchParams({
        start: dateRange.start.toISOString(),
        end: dateRange.end.toISOString()
      })

      const response = await fetch(`/api/admin/tenants/${tenantId}/usage?${params}`)

      if (!response.ok) {
        throw new Error('Failed to get tenant usage')
      }

      return response.json()
    } catch (error) {
      console.error('Error getting tenant usage:', error)
      throw error
    }
  }

  static async extendTrial(tenantId: string, days: number) {
    try {
      const response = await fetch(`/api/admin/tenants/${tenantId}/extend-trial`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days })
      })

      if (!response.ok) {
        throw new Error('Failed to extend trial')
      }

      return response.json()
    } catch (error) {
      console.error('Error extending trial:', error)
      throw error
    }
  }
}
