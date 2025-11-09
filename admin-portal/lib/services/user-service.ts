export interface CreateAdminUserRequest {
  firstName: string
  lastName: string
  email: string
  role: 'SUPER_ADMIN' | 'ADMIN' | 'DEVELOPER' | 'SUPPORT' | 'MARKETING' | 'FINANCE' | 'SALES'
  department: 'ENGINEERING' | 'SUPPORT' | 'MARKETING' | 'FINANCE' | 'SALES' | 'OPERATIONS'
  permissions: string[]
  temporaryPassword?: string
  sendWelcomeEmail?: boolean
}

export interface UpdateAdminUserRequest {
  firstName?: string
  lastName?: string
  role?: string
  department?: string
  permissions?: string[]
  isActive?: boolean
  phone?: string
  position?: string
}

export interface CreateTenantUserRequest {
  firstName: string
  lastName: string
  email: string
  role: 'ADMIN' | 'MANAGER' | 'TECHNICIAN' | 'READONLY'
  tenantId: string
  sendWelcomeEmail?: boolean
}

export class UserService {
  // Admin User Management
  static async createAdminUser(data: CreateAdminUserRequest) {
    try {
      const response = await fetch('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error('Failed to create admin user')
      }

      return response.json()
    } catch (error) {
      console.error('Error creating admin user:', error)
      throw error
    }
  }

  static async updateAdminUser(userId: string, data: UpdateAdminUserRequest) {
    try {
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error('Failed to update admin user')
      }

      return response.json()
    } catch (error) {
      console.error('Error updating admin user:', error)
      throw error
    }
  }

  static async deactivateAdminUser(userId: string) {
    try {
      const response = await fetch(`/api/admin/users/${userId}/deactivate`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error('Failed to deactivate user')
      }

      return response.json()
    } catch (error) {
      console.error('Error deactivating user:', error)
      throw error
    }
  }

  static async resetPassword(userId: string) {
    try {
      const response = await fetch(`/api/admin/users/${userId}/reset-password`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error('Failed to reset password')
      }

      return response.json()
    } catch (error) {
      console.error('Error resetting password:', error)
      throw error
    }
  }

  // Tenant User Management
  static async createTenantUser(data: CreateTenantUserRequest) {
    try {
      const response = await fetch('/api/admin/tenant-users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error('Failed to create tenant user')
      }

      return response.json()
    } catch (error) {
      console.error('Error creating tenant user:', error)
      throw error
    }
  }

  static async updateTenantUser(userId: string, data: Partial<CreateTenantUserRequest>) {
    try {
      const response = await fetch(`/api/admin/tenant-users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error('Failed to update tenant user')
      }

      return response.json()
    } catch (error) {
      console.error('Error updating tenant user:', error)
      throw error
    }
  }

  // User Activity and Analytics
  static async getUserActivity(userId: string, limit = 50) {
    try {
      const response = await fetch(`/api/admin/users/${userId}/activity?limit=${limit}`)

      if (!response.ok) {
        throw new Error('Failed to get user activity')
      }

      return response.json()
    } catch (error) {
      console.error('Error getting user activity:', error)
      throw error
    }
  }

  static async getUserSessions(userId: string) {
    try {
      const response = await fetch(`/api/admin/users/${userId}/sessions`)

      if (!response.ok) {
        throw new Error('Failed to get user sessions')
      }

      return response.json()
    } catch (error) {
      console.error('Error getting user sessions:', error)
      throw error
    }
  }

  static async revokeUserSession(userId: string, sessionId: string) {
    try {
      const response = await fetch(`/api/admin/users/${userId}/sessions/${sessionId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error('Failed to revoke session')
      }

      return response.json()
    } catch (error) {
      console.error('Error revoking session:', error)
      throw error
    }
  }
}
