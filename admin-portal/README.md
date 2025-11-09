# AutoCRM Pro Admin Portal

Comprehensive SaaS administration portal for managing AutoCRM Pro tenants, users, subscriptions, and operations.

## Features

### Tenant Management
- Multi-tenant architecture with isolated data
- Complete tenant lifecycle management (create, update, suspend, delete)
- Business information and contact management
- Usage monitoring and limits enforcement
- Trial and subscription management

### User Management
- Role-based access control (RBAC)
- Admin user management with permission settings
- Tenant user management
- Activity tracking and audit logs
- Session management and security

### Subscription & Billing
- Stripe integration for payment processing
- Subscription plan management (Professional, Performance, Enterprise)
- Revenue tracking and financial analytics
- Invoice generation and billing history
- Churn analysis and metrics

### Support Center
- Ticket management system with priorities
- Multi-channel support tracking
- Knowledge base integration
- SLA tracking and metrics
- Customer communication tools

### Marketing Tools
- Campaign management (email, SMS, in-app)
- Announcement system for feature releases
- User segmentation and targeting
- Marketing analytics and conversion tracking

### Developer Tools
- API key management
- Endpoint monitoring and performance tracking
- Integration management (Capricorn, Xero, MYOB, Stripe)
- Webhook configuration and testing
- System logs and debugging

### Analytics & Monitoring
- Real-time dashboards
- Business intelligence metrics
- Usage analytics per tenant
- Performance monitoring
- Financial reporting

## Technology Stack

- **Frontend**: Next.js 14, React 18, TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI
- **Database**: PostgreSQL with Prisma ORM
- **Authentication**: NextAuth.js / Auth0
- **Payment**: Stripe
- **Email**: SendGrid
- **SMS**: Twilio
- **Charts**: Recharts

## Getting Started

### Prerequisites

- Node.js 18+
- PostgreSQL 14+
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env.local
```

3. Configure database:
```bash
npx prisma db push
npx prisma generate
```

4. Run development server:
```bash
npm run dev
```

Access the admin portal at `http://localhost:3001`

## Project Structure

```
admin-portal/
├── app/
│   ├── admin/
│   │   ├── page.tsx                    # Dashboard
│   │   ├── tenants/                    # Tenant management
│   │   ├── users/                      # User management
│   │   ├── subscriptions/              # Billing
│   │   ├── support/                    # Support center
│   │   ├── marketing/                  # Marketing tools
│   │   └── developer/                  # Developer tools
│   ├── layout.tsx                      # Root layout
│   └── globals.css                     # Global styles
├── components/
│   ├── layout/
│   │   └── admin-sidebar.tsx           # Navigation
│   ├── ui/                             # UI components
│   ├── tenants/                        # Tenant components
│   ├── users/                          # User components
│   ├── support/                        # Support components
│   └── marketing/                      # Marketing components
├── lib/
│   ├── utils.ts                        # Utility functions
│   └── services/                       # API services
├── prisma/
│   └── schema.prisma                   # Database schema
└── package.json
```

## Key Services

### TenantService
Manages tenant creation, updates, suspension, and usage tracking.

```typescript
await TenantService.createTenant(tenantData)
await TenantService.updateTenant(tenantId, updates)
await TenantService.suspendTenant(tenantId, reason)
await TenantService.getTenantUsage(tenantId, dateRange)
```

### UserService
Handles admin and tenant user management.

```typescript
await UserService.createAdminUser(userData)
await UserService.updateAdminUser(userId, updates)
await UserService.createTenantUser(tenantUserData)
await UserService.resetPassword(userId)
```

## API Endpoints

### Tenant Management
- `GET /api/admin/tenants` - List all tenants
- `POST /api/admin/tenants` - Create tenant
- `GET /api/admin/tenants/:id` - Get tenant details
- `PATCH /api/admin/tenants/:id` - Update tenant
- `DELETE /api/admin/tenants/:id` - Delete tenant
- `POST /api/admin/tenants/:id/suspend` - Suspend tenant
- `POST /api/admin/tenants/:id/activate` - Activate tenant

### User Management
- `GET /api/admin/users` - List admin users
- `POST /api/admin/users` - Create admin user
- `PATCH /api/admin/users/:id` - Update user
- `POST /api/admin/users/:id/reset-password` - Reset password

### Subscription Management
- `GET /api/admin/subscriptions` - List subscriptions
- `POST /api/admin/subscriptions` - Create subscription
- `PATCH /api/admin/subscriptions/:id` - Update subscription
- `POST /api/admin/subscriptions/:id/cancel` - Cancel subscription

## Environment Variables

```env
# Database
ADMIN_DATABASE_URL=postgresql://user:password@localhost:5432/autocrm_admin

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Email
SENDGRID_API_KEY=SG...
SENDGRID_FROM_EMAIL=noreply@autocrm.com.au

# SMS
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...

# Authentication
NEXTAUTH_SECRET=...
NEXTAUTH_URL=http://localhost:3001

# API URLs
API_BASE_URL=http://localhost:3001
MAIN_APP_API_URL=http://localhost:3000
```

## Database Schema

The admin portal uses Prisma ORM with PostgreSQL. Key models include:

- **Tenant**: Customer accounts with subscription and usage info
- **TenantUser**: Users within tenant accounts
- **TenantWorkshop**: Workshop locations for tenants
- **Subscription**: Billing and subscription management
- **AdminUser**: Admin portal users with roles and permissions
- **SupportTicket**: Customer support tickets
- **UsageMetric**: Usage analytics and metrics
- **NotificationTemplate**: Email/SMS templates
- **FeatureFlag**: Feature rollout management

## Deployment

### Production Build
```bash
npm run build
npm start
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3001
CMD ["npm", "start"]
```

## Development

### Code Style
- TypeScript for type safety
- ESLint for code linting
- Prettier for code formatting

### Testing
```bash
npm run test
npm run test:coverage
```

### Database Migrations
```bash
npx prisma migrate dev --name migration_name
npx prisma migrate deploy
npx prisma studio  # Visual database editor
```

## Security

- Role-based access control (RBAC)
- Session management with secure tokens
- Encrypted sensitive configuration
- Audit logging for all admin actions
- Rate limiting on API endpoints
- SQL injection protection via Prisma
- XSS prevention with React sanitization

## Performance

- Server-side rendering with Next.js
- Optimized database queries with Prisma
- Image optimization
- Code splitting and lazy loading
- Caching strategies
- CDN integration ready

## Monitoring & Logging

- Sentry for error tracking
- Google Analytics for usage
- Structured logging
- Performance monitoring
- Alert system for critical errors

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request
4. Ensure all tests pass

## Support

For issues and questions, contact: support@autocrm.com.au

## License

Proprietary - AutoCRM Pro

## Version

v1.0.0
