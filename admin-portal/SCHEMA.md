# AutoCRM Pro - Database Schema Documentation

## Overview

This document describes the complete database schema for the AutoCRM Pro automotive repair workshop SaaS platform. The schema is built with Prisma ORM and PostgreSQL as the datasource.

**Version**: 1.0.0
**Last Updated**: November 2024
**Database**: PostgreSQL 12+

---

## Table of Contents

1. [Architecture](#architecture)
2. [Enums](#enums)
3. [Data Models](#data-models)
4. [Relationships](#relationships)
5. [Setup Instructions](#setup-instructions)
6. [Seed Data](#seed-data)
7. [Best Practices](#best-practices)

---

## Architecture

### Multi-Tenancy

The entire database architecture is designed around a **multi-tenant model** where the `Organization` entity serves as the root entity for data isolation. All entities include an `organizationId` field to ensure complete data isolation between organizations.

**Key Principles:**
- Each organization operates in complete isolation
- All queries must filter by `organizationId`
- Cascade delete ensures no orphaned records remain when an organization is deleted
- Perfect for SaaS deployments with multiple workshop locations/clients

### Module Structure

The schema supports 8 major functional modules:

1. **Organization & Multi-Tenancy**: Core organizational structure and configuration
2. **Users & Authentication**: User accounts, roles, sessions, and preferences
3. **CRM**: Customer relationship management (customers, vehicles, communications)
4. **Quotes & Service Jobs**: Quoting and job management workflow
5. **HRM**: Human resource management (employees, scheduling, payroll)
6. **MAP**: Maintenance and Parts management (inventory, suppliers, orders)
7. **ERP**: Enterprise resource planning (invoicing, accounting, payments)
8. **Audit & Analytics**: Logging, notifications, and reporting

---

## Enums

### Organization & User Enums

#### `OrganizationType`
```
INDEPENDENT_SHOP        // Single mechanic or small shop
FRANCHISE               // Franchised workshop
DEALERSHIP              // Car dealership with service
FLEET_MANAGEMENT        // Fleet management company
ENTERPRISE              // Large multi-location organization
MULTI_LOCATION          // Multiple workshop locations
```

#### `UserRole`
```
SUPER_ADMIN             // Full system access
ADMIN                   // Full organization access
MANAGER                 // Manage staff and jobs
SERVICE_ADVISOR         // Customer-facing advisor
MECHANIC                // Perform repairs/maintenance
PARTS_MANAGER           // Manage inventory
ACCOUNTANT              // Financial operations
CUSTOMER_SERVICE        // Customer support
CUSTOMER                // Customer access
EMPLOYEE                // Base employee role
```

#### `UserStatus`
```
ACTIVE                  // User can log in
INACTIVE                // User cannot log in
SUSPENDED               // Temporarily disabled
PENDING_ACTIVATION      // Awaiting activation
ARCHIVED                // Permanently inactive (soft-deleted)
```

### CRM Enums

#### `CustomerType`
```
INDIVIDUAL              // Individual customer
BUSINESS                // Business/corporate customer
GOVERNMENT              // Government organization
```

#### `CustomerStatus`
```
LEAD                    // Potential customer
ACTIVE                  // Current customer
INACTIVE                // Inactive customer
BLACKLIST               // Blocked customer
```

#### `VehicleStatus`
```
ACTIVE                  // In active service
INACTIVE                // Not in use
RETIRED                 // Retired from service
IN_SERVICE              // Currently being serviced
```

### Service & Quoting Enums

#### `JobType`
```
MAINTENANCE             // Regular maintenance
REPAIR                  // Repair work
INSPECTION              // Vehicle inspection
DIAGNOSTIC              // Diagnostic work
CUSTOMIZATION           // Custom work
OTHER                   // Other service type
```

#### `ServiceJobStatus`
```
QUOTE_PENDING           // Awaiting quote approval
QUOTE_SENT              // Quote sent to customer
QUOTE_APPROVED          // Quote approved by customer
SCHEDULED               // Job scheduled
IN_PROGRESS             // Work in progress
AWAITING_PARTS          // Waiting for parts
QUALITY_CHECK           // Quality inspection
AWAITING_PICKUP         // Ready for customer pickup
COMPLETED               // Job completed
INVOICED                // Invoice created
PAID                    // Payment received
CANCELLED               // Job cancelled
ARCHIVED                // Historical record
```

#### `ServiceJobPriority`
```
LOW                     // Low priority
MEDIUM                  // Normal priority
HIGH                    // High priority
URGENT                  // Very urgent
CRITICAL                // Critical/emergency
```

#### `QuoteStatus`
```
DRAFT                   // Quote being prepared
SENT                    // Quote sent to customer
VIEWED                  // Customer viewed quote
ACCEPTED                // Customer accepted
REJECTED                // Customer rejected
EXPIRED                 // Quote expired
CONVERTED               // Converted to service job
ARCHIVED                // Archived quote
```

### HRM Enums

#### `EmployeeRole`
```
OWNER                   // Shop owner
MANAGER                 // Workshop manager
MECHANIC                // Technician/mechanic
SERVICE_ADVISOR         // Service advisor
APPRENTICE              // Apprentice/trainee
PARTS_MANAGER           // Parts inventory manager
ACCOUNTANT              // Finance/accounting
ADMINISTRATIVE          // Administrative staff
```

#### `EmployeeStatus`
```
ACTIVE                  // Currently employed
ON_LEAVE                // Currently on leave
SUSPENDED               // Temporarily suspended
TERMINATED              // Employment terminated
ARCHIVED                // Historical record
```

#### `LeaveType`
```
VACATION                // Paid vacation
SICK                    // Sick leave
PERSONAL                // Personal leave
MATERNITY               // Maternity leave
PATERNITY               // Paternity leave
UNPAID                  // Unpaid leave
OTHER                   // Other leave type
```

#### `ShiftStatus`
```
SCHEDULED               // Shift scheduled
CONFIRMED               // Employee confirmed
CANCELLED               // Shift cancelled
COMPLETED               // Shift completed
```

#### `PayrollStatus`
```
DRAFT                   // Being prepared
PENDING_APPROVAL        // Awaiting approval
APPROVED                // Approved by manager
PROCESSING              // Being processed
COMPLETED               // Payroll completed
PAID                    // Payment processed
ARCHIVED                // Historical record
```

### Inventory & Parts Enums

#### `PartStatus`
```
ACTIVE                  // Available for purchase
DISCONTINUED            // No longer available
OBSOLETE                // Obsolete part
ARCHIVED                // Historical record
```

#### `PartLocation`
```
SHELF_A through SHELF_Z // Physical shelf locations
CABINET_A through CABINET_E // Cabinet storage
WAREHOUSE               // Warehouse storage
EXTERNAL_SUPPLIER       // At external supplier
```

#### `InventoryAdjustmentType`
```
STOCK_CORRECTION        // Inventory count correction
DAMAGE                  // Damaged stock
LOSS                    // Inventory loss
RETURN                  // Return from job
OBSOLESCENCE           // Marked obsolete
TRANSFER                // Transfer between locations
SHRINKAGE               // Unaccounted loss
WASTE                   // Waste/scrap
```

#### `SupplierStatus`
```
ACTIVE                  // Active supplier
INACTIVE                // Inactive supplier
BLOCKED                 // Cannot purchase from
ARCHIVED                // Historical record
```

#### `PurchaseOrderStatus`
```
DRAFT                   // Being prepared
SUBMITTED               // Submitted to supplier
ACKNOWLEDGED            // Supplier acknowledged
PARTIAL_RECEIVED        // Partially received
RECEIVED                // Fully received
COMPLETED               // PO completed
CANCELLED               // Order cancelled
ARCHIVED                // Historical record
```

#### `WarrantyStatus`
```
ACTIVE                  // Currently active
EXPIRED                 // Warranty expired
VOIDED                  // Warranty voided
CLAIMED                 // Warranty claim made
ARCHIVED                // Historical record
```

#### `RecallSeverity`
```
MINOR                   // Minor issue
MAJOR                   // Major issue
CRITICAL                // Critical issue
SAFETY_CRITICAL         // Safety-critical issue
```

### ERP Enums

#### `InvoiceStatus`
```
DRAFT                   // Draft invoice
SENT                    // Invoice sent to customer
VIEWED                  // Customer viewed invoice
PARTIALLY_PAID          // Partially paid
PAID                    // Fully paid
OVERDUE                 // Payment overdue
CANCELLED               // Invoice cancelled
REFUNDED                // Refunded
ARCHIVED                // Historical record
```

#### `PaymentMethod`
```
CASH                    // Cash payment
CHECK                   // Check payment
CREDIT_CARD             // Credit card
DEBIT_CARD              // Debit card
BANK_TRANSFER           // Electronic transfer
ACH                     // ACH payment
CRYPTOCURRENCY          // Cryptocurrency
MOBILE_PAYMENT          // Mobile payment (Apple Pay, etc)
MULTIPLE                // Multiple payment methods
```

#### `PaymentStatus`
```
PENDING                 // Awaiting payment
PROCESSING              // Payment processing
COMPLETED               // Payment completed
FAILED                  // Payment failed
REFUNDED                // Refund processed
DISPUTED                // Payment disputed
CANCELLED               // Payment cancelled
ARCHIVED                // Historical record
```

### Integration & Notification Enums

#### `IntegrationType`
```
ACCOUNTING_SOFTWARE     // QuickBooks, FreshBooks, etc.
PAYMENT_GATEWAY         // Stripe, PayPal, Square
EMAIL_SERVICE           // SendGrid, Mailgun
SMS_SERVICE             // Twilio
CRM_INTEGRATION         // HubSpot, Salesforce
PARTS_SUPPLIER          // OEM or parts supplier APIs
GPS_TRACKING            // Vehicle GPS tracking
CALENDAR_SYNC           // Google Calendar, Outlook
DOCUMENT_MANAGEMENT     // Document storage
API_INTEGRATION         // Custom API integration
```

#### `NotificationType`
```
JOB_REMINDER            // Service job reminders
INVOICE_REMINDER        // Invoice payment reminder
PAYMENT_RECEIVED        // Payment confirmation
PART_ARRIVAL            // Parts arrived notification
LOW_STOCK_ALERT         // Low inventory alert
APPOINTMENT_CONFIRMATION // Appointment confirmed
SERVICE_COMPLETION      // Service job completed
NEW_CUSTOMER_MESSAGE    // New customer message
REPORT_READY            // Report generation complete
SYSTEM_ALERT            // System alerts
MAINTENANCE_DUE         // Vehicle maintenance due
WARRANTY_EXPIRY         // Warranty expiring soon
```

#### `NotificationStatus`
```
PENDING                 // Scheduled notification
SENT                    // Notification sent
FAILED                  // Sending failed
READ                    // User read notification
ARCHIVED                // Archived notification
```

---

## Data Models

### Organization & Multi-Tenancy

#### `Organization`
Root entity for multi-tenant data isolation.

**Fields:**
- `id` (String): Unique identifier
- `name` (String): Organization name
- `type` (OrganizationType): Type of organization
- `registrationNumber` (String): Business registration number
- `taxId` (String): Tax identification number
- `email` (String): Organization email
- `phone` (String): Contact phone number
- `website` (String): Website URL
- `address*` (String): Physical address fields
- `timezone` (String): Organization timezone
- `currency` (String): Default currency code
- `logo` (String): Logo URL
- `subscription` (String): Current subscription plan
- `subscriptionExpiresAt` (DateTime): Subscription expiration
- `isActive` (Boolean): Active status
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp
- `deletedAt` (DateTime): Soft delete timestamp

**Indexes:**
- `isActive` - Active organizations
- `type` - Organization type filtering
- `createdAt` - Chronological queries

**Relations:**
- `users` ↔ User[] - Organization users
- `customers` ↔ Customer[] - Organization customers
- `vehicles` ↔ Vehicle[] - Organization vehicles
- `employees` ↔ Employee[] - Organization employees
- `invoices` ↔ Invoice[] - Organization invoices
- `serviceJobs` ↔ ServiceJob[] - Service jobs
- (and many more...)

---

#### `Location`
Physical workshop locations for multi-location organizations.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `name` (String): Location name
- `address*` (String): Physical address
- `phone` (String): Location phone
- `email` (String): Location email
- `isMainLocation` (Boolean): Primary location flag
- `isActive` (Boolean): Active status
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

**Indexes:**
- `organizationId` - Locations by organization
- `isMainLocation` - Find main location

---

#### `OrganizationSettings`
Organization-level configuration and settings.

**Fields:**
- 25+ configuration fields for business rules
- Examples: `workingHoursStart/End`, `lowStockThreshold`, `invoicePrefix`, etc.

---

### Users & Authentication

#### `User`
System users with role-based access control.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `email` (String): Email address (unique per org)
- `firstName` (String): First name
- `lastName` (String): Last name
- `phoneNumber` (String): Phone number
- `avatar` (String): Avatar URL
- `role` (UserRole): User role
- `status` (UserStatus): Current status
- `passwordHash` (String): Hashed password
- `passwordResetToken` (String): Reset token
- `passwordResetExpiresAt` (DateTime): Reset expiration
- `lastLoginAt` (DateTime): Last login timestamp
- `lastLoginIp` (String): Last login IP address
- `emailVerified` (Boolean): Email verification status
- `twoFactorEnabled` (Boolean): 2FA enabled
- `loginAttempts` (Int): Failed login attempts
- `lockedUntil` (DateTime): Account lock time
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp
- `deletedAt` (DateTime): Soft delete timestamp

**Indexes:**
- `organizationId` - Users by organization
- `email` - Email lookups
- `role` - Role-based queries
- `status` - Status filtering
- `lastLoginAt` - Activity analysis

**Relations:**
- `organization` ↔ Organization - Parent organization
- `employee` ↔ Employee? - Associated employee record
- `assignedServiceJobs` ↔ ServiceJob[] - Assigned jobs
- `assignedQuotes` ↔ Quote[] - Assigned quotes
- `sessions` ↔ Session[] - Login sessions
- `notifications` ↔ Notification[] - User notifications

---

#### `Session`
User login sessions for security tracking.

**Fields:**
- `id` (String): Session ID
- `userId` (String): Associated user
- `token` (String): Session token (unique)
- `ipAddress` (String): Login IP address
- `userAgent` (String): Browser user agent
- `expiresAt` (DateTime): Session expiration
- `createdAt` (DateTime): Creation timestamp

**Relations:**
- `user` ↔ User - Parent user

---

#### `UserPreferences`
Per-user application preferences.

**Fields:**
- Theme preferences
- Language settings
- Notification preferences
- UI layout preferences

---

### CRM Module

#### `Customer`
Customer records with contact and loyalty information.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `firstName` (String): First name
- `lastName` (String): Last name
- `email` (String): Email (unique per org)
- `phoneNumber` (String): Phone number
- `type` (CustomerType): Individual or Business
- `status` (CustomerStatus): Customer status
- `address*` (String): Physical address
- `companyName` (String): For business customers
- `taxId` (String): Tax ID
- `loyaltyPoints` (Int): Loyalty program points
- `totalSpent` (Float): Total revenue from customer
- `averageRating` (Float): Customer satisfaction rating
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp
- `deletedAt` (DateTime): Soft delete timestamp

**Relations:**
- `vehicles` ↔ Vehicle[] - Customer vehicles
- `serviceJobs` ↔ ServiceJob[] - Service history
- `quotes` ↔ Quote[] - Quote history
- `communications` ↔ CustomerCommunication[] - Communications
- `invoices` ↔ Invoice[] - Invoice history

---

#### `Vehicle`
Customer vehicles requiring service.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `customerId` (String): Owner customer
- `vin` (String): Vehicle Identification Number (unique)
- `licensePlate` (String): License plate (unique)
- `year` (Int): Model year
- `make` (String): Manufacturer
- `model` (String): Model name
- `trim` (String): Trim level
- `color` (String): Vehicle color
- `bodyType` (String): Body type (sedan, truck, etc)
- `fuelType` (String): Fuel type (gasoline, diesel, hybrid)
- `transmission` (String): Transmission type
- `engineSize` (String): Engine displacement
- `mileage` (Int): Current mileage
- `status` (VehicleStatus): Current status
- `serviceHistory` (String): Service history notes
- `insuranceCompany` (String): Insurance provider
- `insurancePolicyNumber` (String): Policy number
- `registrationExpiry` (DateTime): Registration expiration
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

**Relations:**
- `customer` ↔ Customer - Owner
- `serviceJobs` ↔ ServiceJob[] - Service history
- `quotes` ↔ Quote[] - Quotes for this vehicle
- `maintenancePlans` ↔ MaintenancePlan[] - Maintenance plans

---

#### `CustomerCommunication`
Communication history with customers (calls, emails, messages).

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `customerId` (String): Customer
- `type` (CommunicationType): Communication type
- `direction` (INBOUND | OUTBOUND): Direction
- `subject` (String): Subject/title
- `content` (String): Message content
- `duration` (Int): Duration in seconds (for calls)
- `communicatedBy` (String): User who communicated
- `communicatedAt` (DateTime): Communication timestamp
- `createdAt` (DateTime): Record creation

**Types:**
- PHONE, EMAIL, SMS, IN_PERSON, CHAT, VIDEO_CALL

---

### Quotes & Service Jobs

#### `Quote`
Service quotes/estimates for customers.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `customerId` (String): Customer
- `vehicleId` (String): Vehicle
- `quoteNumber` (String): Quote number
- `status` (QuoteStatus): Current status
- `estimatedCost` (Float): Total estimated cost
- `laborCost` (Float): Labor cost
- `partsCost` (Float): Parts cost
- `taxAmount` (Float): Tax amount
- `grandTotal` (Float): Total with tax
- `description` (String): Work description
- `validUntil` (DateTime): Quote expiration date
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

**Relations:**
- `quoteItems` ↔ QuoteItem[] - Line items
- `serviceJob` ↔ ServiceJob? - Associated job

---

#### `QuoteItem`
Line items within a quote.

**Fields:**
- `id` (String): Unique identifier
- `quoteId` (String): Parent quote
- `partId` (String): Associated part (optional)
- `description` (String): Item description
- `quantity` (Float): Item quantity
- `unitPrice` (Float): Price per unit
- `totalPrice` (Float): Line total
- `itemType` (String): LABOR, PART, SERVICE, DIAGNOSTIC, OTHER

---

#### `ServiceJob`
Service repair jobs with status tracking.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `customerId` (String): Customer
- `vehicleId` (String): Vehicle
- `quoteId` (String): Originating quote (optional, unique)
- `jobNumber` (String): Job number (unique)
- `jobType` (JobType): Type of service
- `status` (ServiceJobStatus): Current status
- `priority` (ServiceJobPriority): Job priority
- `estimatedCost` (Float): Estimated total
- `actualCost` (Float): Actual cost when completed
- `laborCost` (Float): Labor charges
- `partsCost` (Float): Parts charges
- `description` (String): Work description
- `scheduledStartDate` (DateTime): Scheduled start
- `scheduledEndDate` (DateTime): Scheduled completion
- `actualStartDate` (DateTime): Actual start
- `actualEndDate` (DateTime): Actual completion
- `assignedMechanicId` (String): Assigned technician
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

**Status Progression:**
QUOTE_PENDING → QUOTE_SENT → QUOTE_APPROVED → SCHEDULED → IN_PROGRESS → AWAITING_PARTS → QUALITY_CHECK → AWAITING_PICKUP → COMPLETED → INVOICED → PAID

**Relations:**
- `jobTasks` ↔ JobTask[] - Work breakdown
- `jobParts` ↔ JobPart[] - Parts used
- `jobTimesheets` ↔ JobTimesheet[] - Labor tracking

---

#### `JobTask`
Breakdown of work items within a service job.

**Fields:**
- `id` (String): Unique identifier
- `serviceJobId` (String): Parent job
- `description` (String): Task description
- `estimatedHours` (Float): Estimated labor hours
- `actualHours` (Float): Actual labor hours
- `status` (TaskStatus): Current status
- `priority` (TaskPriority): Task priority
- `assignedTo` (String): Assigned employee
- `completedAt` (DateTime): Completion timestamp

**Status:**
NOT_STARTED | IN_PROGRESS | COMPLETED | BLOCKED

---

#### `JobPart`
Parts used/reserved for a service job.

**Fields:**
- `id` (String): Unique identifier
- `serviceJobId` (String): Parent job
- `partId` (String): Part being used
- `quantity` (Float): Quantity used
- `issuedDate` (DateTime): When part was issued
- `costPrice` (Float): Cost to workshop
- `sellingPrice` (Float): Price to customer

---

#### `JobTimesheet`
Labor tracking for accurate job costing.

**Fields:**
- `id` (String): Unique identifier
- `serviceJobId` (String): Parent job
- `employeeId` (String): Technician
- `startTime` (DateTime): Work start time
- `endTime` (DateTime): Work end time
- `breakMinutes` (Int): Break duration
- `billableHours` (Float): Hours to charge customer
- `internalNotes` (String): Notes

---

### HRM Module

#### `Employee`
Employee records with employment details.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `userId` (String): Associated user account (optional)
- `firstName` (String): First name
- `lastName` (String): Last name
- `email` (String): Email (unique per org)
- `phoneNumber` (String): Phone number
- `role` (EmployeeRole): Job role
- `status` (EmployeeStatus): Employment status
- `hireDate` (DateTime): Hire date
- `terminationDate` (DateTime): Termination date (if applicable)
- `baseSalary` (Float): Annual salary
- `hourlyRate` (Float): Hourly rate
- `bankAccount` (String): Bank account for direct deposit
- `ssn` (String): Social security number (encrypted)
- `emergencyContact` (String): Emergency contact name
- `emergencyPhone` (String): Emergency contact phone
- `certifications` (String[]): List of certifications
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

**Relations:**
- `skills` ↔ EmployeeSkill[] - Employee skills
- `schedules` ↔ Schedule[] - Work schedules
- `attendance` ↔ Attendance[] - Attendance records
- `timesheets` ↔ Timesheet[] - Weekly timesheets
- `payrollRecords` ↔ PayrollRecord[] - Payroll history

---

#### `EmployeeSkill`
Certifications and skills for employees.

**Fields:**
- `id` (String): Unique identifier
- `employeeId` (String): Employee
- `skillName` (String): Skill name
- `proficiencyLevel` (String): BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
- `certificationNumber` (String): Certification ID
- `expiryDate` (DateTime): Certification expiry

---

#### `Schedule`
Employee work schedules with shift management.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `employeeId` (String): Employee
- `shiftDate` (DateTime): Shift date
- `shiftStartTime` (String): Start time (HH:MM)
- `shiftEndTime` (String): End time (HH:MM)
- `breakStartTime` (String): Break start time
- `breakEndTime` (String): Break end time
- `status` (ShiftStatus): Current status
- `notes` (String): Special notes

---

#### `Attendance`
Employee attendance tracking.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `employeeId` (String): Employee
- `attendanceDate` (DateTime): Date of attendance
- `clockInTime` (DateTime): Clock in timestamp
- `clockOutTime` (DateTime): Clock out timestamp
- `status` (AttendanceStatus): PRESENT, ABSENT, LATE, EARLY_LEAVE, ON_LEAVE
- `overtimeHours` (Float): Overtime hours
- `notes` (String): Attendance notes

---

#### `LeaveRequest`
Employee leave/time-off requests.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `employeeId` (String): Employee
- `leaveType` (LeaveType): Type of leave
- `startDate` (DateTime): Leave start date
- `endDate` (DateTime): Leave end date
- `numberOfDays` (Float): Number of days
- `status` (LeaveStatus): PENDING, APPROVED, REJECTED
- `approvedBy` (String): Approver user ID
- `approvedDate` (DateTime): Approval date
- `reason` (String): Reason for leave
- `attachments` (String[]): Document attachments

---

#### `Timesheet`
Weekly timesheet tracking for payroll.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `employeeId` (String): Employee
- `weekStartDate` (DateTime): Week start date
- `weekEndDate` (DateTime): Week end date
- `totalHours` (Float): Total hours worked
- `regularHours` (Float): Regular hours
- `overtimeHours` (Float): Overtime hours
- `status` (TimesheetStatus): DRAFT, SUBMITTED, APPROVED, PAID
- `submittedDate` (DateTime): Submission date
- `approvedBy` (String): Approver user ID
- `approvedDate` (DateTime): Approval date
- `notes` (String): Timesheet notes

---

#### `PayrollRecord`
Payroll calculation and payment records.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `employeeId` (String): Employee
- `payrollPeriod` (String): Period (e.g., "2024-01")
- `payrollDate` (DateTime): Payment date
- `baseSalary` (Float): Base salary for period
- `overtimeHours` (Float): Overtime hours
- `overtimeRate` (Float): Overtime rate multiplier
- `overtimeAmount` (Float): Overtime pay
- `bonusAmount` (Float): Bonus amount
- `grossSalary` (Float): Gross pay
- `totalDeductions` (Float): Total deductions
- `netSalary` (Float): Net pay
- `status` (PayrollStatus): Processing status
- `notes` (String): Notes

**Status Progression:**
DRAFT → PENDING_APPROVAL → APPROVED → PROCESSING → COMPLETED → PAID

**Relations:**
- `deductions` ↔ PayrollDeduction[] - Deduction details
- `payments` ↔ PayrollPayment[] - Payment methods

---

#### `PayrollDeduction`
Individual deductions from payroll.

**Fields:**
- `id` (String): Unique identifier
- `payrollRecordId` (String): Parent payroll
- `deductionType` (String): TAX, INSURANCE, PENSION, LOAN, GARNISHMENT, OTHER
- `description` (String): Deduction description
- `amount` (Float): Deduction amount

---

#### `PayrollPayment`
Payment method/record for payroll.

**Fields:**
- `id` (String): Unique identifier
- `payrollRecordId` (String): Parent payroll
- `paymentMethod` (PaymentMethod): Payment method
- `amount` (Float): Payment amount
- `paymentDate` (DateTime): Payment date
- `transactionId` (String): Transaction reference
- `status` (PaymentStatus): Payment status

---

### MAP Module (Maintenance & Parts)

#### `Part`
Inventory parts with pricing and location tracking.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `partNumber` (String): Unique part number
- `name` (String): Part name
- `category` (String): Part category
- `manufacturer` (String): Manufacturer name
- `manufacturerPartNumber` (String): OEM part number
- `description` (String): Part description
- `costPrice` (Float): Cost to workshop
- `sellingPrice` (Float): Price to customer
- `quantity` (Int): Current quantity
- `minimumStockLevel` (Int): Low stock threshold
- `maximumStockLevel` (Int): Maximum stock level
- `reorderQuantity` (Int): Reorder amount
- `location` (PartLocation): Storage location
- `barcode` (String): Barcode (unique per org)
- `status` (PartStatus): Availability status
- `serialNumberRequired` (Boolean): Serial number tracking
- `lastRestockDate` (DateTime): Last restock date
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

**Indexes:**
- `organizationId` - Parts by organization
- `partNumber` - Part lookup
- `barcode` - Barcode scanning
- `status` - Active parts
- `quantity` - Inventory levels

**Relations:**
- `inventoryAdjustments` ↔ InventoryAdjustment[] - Adjustment history
- `supplierParts` ↔ SupplierPart[] - Supplier catalog

---

#### `PartInventory`
Multi-location inventory tracking with bin locations.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `partId` (String): Part reference
- `locationId` (String): Workshop location
- `binNumber` (String): Bin/shelf location
- `quantity` (Int): Quantity at location
- `serialNumbers` (String[]): Serial numbers if tracked
- `lastCountDate` (DateTime): Last inventory count
- `notes` (String): Notes

---

#### `InventoryAdjustment`
Inventory adjustments for reconciliation and corrections.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `partId` (String): Part being adjusted
- `adjustmentType` (InventoryAdjustmentType): Type of adjustment
- `quantity` (Int): Quantity adjusted
- `reason` (String): Reason for adjustment
- `reference` (String): Reference (job number, etc)
- `adjustedBy` (String): User who made adjustment
- `adjustmentDate` (DateTime): Adjustment date
- `notes` (String): Additional notes

---

#### `Supplier`
Parts suppliers and vendors.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `supplierName` (String): Supplier name
- `contactPerson` (String): Primary contact
- `email` (String): Contact email
- `phoneNumber` (String): Contact phone
- `faxNumber` (String): Fax number
- `addressLine1` (String): Address
- `city` (String): City
- `state` (String): State
- `postalCode` (String): Postal code
- `paymentTerms` (String): NET_15, NET_30, NET_60, etc.
- `leadTimeDays` (Int): Average lead time
- `rating` (Float): Supplier rating (0-5)
- `totalOrdersCount` (Int): Total orders
- `totalSpent` (Float): Total spending
- `status` (SupplierStatus): Active status
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

---

#### `PurchaseOrder`
Purchase orders to suppliers.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `supplierId` (String): Supplier
- `poNumber` (String): PO number (unique per org)
- `status` (PurchaseOrderStatus): Current status
- `orderDate` (DateTime): Order date
- `expectedDeliveryDate` (DateTime): Expected delivery
- `actualDeliveryDate` (DateTime): Actual delivery
- `totalAmount` (Float): Order total
- `taxAmount` (Float): Tax
- `shippingCost` (Float): Shipping cost
- `discountAmount` (Float): Discount
- `grandTotal` (Float): Final total
- `paymentStatus` (PaymentStatus): Payment status
- `notes` (String): Order notes

**Status Progression:**
DRAFT → SUBMITTED → ACKNOWLEDGED → PARTIAL_RECEIVED → RECEIVED → COMPLETED

**Relations:**
- `poItems` ↔ PurchaseOrderItem[] - Line items

---

#### `PurchaseOrderItem`
Line items in a purchase order.

**Fields:**
- `id` (String): Unique identifier
- `purchaseOrderId` (String): Parent PO
- `partId` (String): Part being ordered
- `quantity` (Int): Quantity ordered
- `unitPrice` (Float): Price per unit
- `totalPrice` (Float): Line total
- `quantityReceived` (Int): Received quantity
- `notes` (String): Item notes

---

#### `PartReceipt`
Goods receipt/receiving documentation.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `purchaseOrderId` (String): Related PO
- `receiptNumber` (String): Receipt number (unique)
- `status` (ReceiptStatus): PENDING, PARTIAL, COMPLETE
- `totalItemsReceived` (Int): Items received count
- `totalItemsExpected` (Int): Items expected
- `receivedBy` (String): Receiving employee
- `receivedDate` (DateTime): Receipt date
- `inspectedBy` (String): Quality inspector
- `inspectionDate` (DateTime): Inspection date
- `notes` (String): Receipt notes

**Relations:**
- `receiptItems` ↔ PartReceiptItem[] - Received items

---

#### `MaintenancePlan`
Recurring maintenance plans for vehicles.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `vehicleId` (String): Vehicle
- `planName` (String): Plan name
- `status` (MaintenancePlanStatus): ACTIVE, INACTIVE, COMPLETED
- `isRecurring` (Boolean): Recurring plan
- `recurrenceInterval` (Int): Months between maintenance
- `recurrenceMileage` (Int): Mileage between maintenance
- `lastMaintenanceDate` (DateTime): Last service date
- `nextMaintenanceDate` (DateTime): Next service date
- `createdAt` (DateTime): Creation timestamp

---

#### `MaintenanceTask`
Individual maintenance tasks within a plan.

**Fields:**
- `id` (String): Unique identifier
- `maintenancePlanId` (String): Parent plan
- `description` (String): Task description
- `estimatedCost` (Float): Estimated cost
- `actualCost` (Float): Actual cost
- `status` (MaintenanceTaskStatus): Task status
- `scheduledDate` (DateTime): Scheduled date
- `completedDate` (DateTime): Completion date

---

#### `Warranty`
Vehicle/part warranties.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `vehicleId` (String): Vehicle (optional)
- `partId` (String): Part (optional)
- `warrantyNumber` (String): Warranty ID
- `warrantyType` (WarrantyType): Type of warranty
- `startDate` (DateTime): Start date
- `endDate` (DateTime): Expiration date
- `mileageLimit` (Int): Mileage limit
- `coveragePercentage` (Float): Coverage percentage
- `maximumCoverageAmount` (Float): Max coverage amount
- `status` (WarrantyStatus): Current status
- `notes` (String): Warranty notes

---

#### `Recall`
Vehicle recalls and service bulletins.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `vehicleId` (String): Vehicle
- `recallNumber` (String): Recall ID (unique)
- `manufacturer` (String): Issuing manufacturer
- `title` (String): Recall title
- `description` (String): Recall details
- `severity` (RecallSeverity): Severity level
- `status` (RecallStatus): OPEN, IN_PROGRESS, COMPLETED, CLOSED
- `issueDate` (DateTime): Recall date
- `serviceDate` (DateTime): Service date (if completed)

---

### ERP Module (Enterprise Resource Planning)

#### `Invoice`
Customer invoices for services rendered.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `customerId` (String): Customer
- `vehicleId` (String): Vehicle (optional)
- `serviceJobId` (String): Related job (optional)
- `invoiceNumber` (String): Invoice number (unique)
- `status` (InvoiceStatus): Current status
- `invoiceDate` (DateTime): Invoice date
- `dueDate` (DateTime): Due date
- `paidDate` (DateTime): Payment date (if paid)
- `totalAmount` (Float): Subtotal
- `taxAmount` (Float): Tax
- `discountAmount` (Float): Discount
- `grandTotal` (Float): Total with tax
- `amountPaid` (Float): Amount received
- `amountDue` (Float): Outstanding balance
- `notes` (String): Invoice notes
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

**Status Progression:**
DRAFT → SENT → VIEWED → PARTIALLY_PAID → PAID

**Indexes:**
- `organizationId` - Invoices by organization
- `customerId` - Customer invoices
- `status` - Status filtering
- `invoiceDate` - Date range queries
- `amountDue` - Outstanding balance

**Relations:**
- `lineItems` ↔ InvoiceLineItem[] - Invoice items
- `payments` ↔ Payment[] - Associated payments

---

#### `InvoiceLineItem`
Individual line items on an invoice.

**Fields:**
- `id` (String): Unique identifier
- `invoiceId` (String): Parent invoice
- `description` (String): Item description
- `quantity` (Float): Item quantity
- `unitPrice` (Float): Unit price
- `totalPrice` (Float): Line total
- `itemType` (String): LABOR, PART, SERVICE, DIAGNOSTIC, OTHER
- `createdAt` (DateTime): Creation timestamp

---

#### `Payment`
Payment records for invoices.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `invoiceId` (String): Invoice being paid
- `paymentMethod` (PaymentMethod): Payment method
- `amount` (Float): Payment amount
- `paymentDate` (DateTime): Payment date
- `status` (PaymentStatus): Payment status
- `transactionId` (String): Transaction reference
- `referenceNumber` (String): Check number, etc.
- `notes` (String): Payment notes
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

**Relations:**
- `invoice` ↔ Invoice - Associated invoice

---

#### `ChartOfAccount`
Accounting chart of accounts for general ledger.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `accountCode` (String): Account code (unique)
- `accountName` (String): Account name
- `accountType` (String): ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
- `description` (String): Account description
- `balance` (Float): Current balance
- `isActive` (Boolean): Active account
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

---

#### `JournalEntry`
General ledger journal entries with double-entry bookkeeping.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `entryNumber` (String): Entry number (unique)
- `entryDate` (DateTime): Entry date
- `totalDebit` (Float): Total debits
- `totalCredit` (Float): Total credits
- `description` (String): Entry description
- `isApproved` (Boolean): Approval status
- `approvedBy` (String): Approver user ID
- `approvedDate` (DateTime): Approval date
- `createdAt` (DateTime): Creation timestamp

**Relations:**
- `lines` ↔ JournalEntryLine[] - Entry lines

---

#### `JournalEntryLine`
Individual line items in journal entries.

**Fields:**
- `id` (String): Unique identifier
- `journalEntryId` (String): Parent entry
- `accountId` (String): Chart of account
- `debit` (Float): Debit amount
- `credit` (Float): Credit amount
- `description` (String): Line description

---

#### `Expense`
Business expense tracking.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `expenseCategory` (String): Category (RENT, UTILITIES, SUPPLIES, etc.)
- `amount` (Float): Expense amount
- `expenseDate` (DateTime): Expense date
- `paymentMethod` (PaymentMethod): Payment method
- `reference` (String): Invoice/receipt reference
- `description` (String): Description
- `attachments` (String[]): Receipt images
- `approvedBy` (String): Approver user ID
- `status` (String): PENDING, APPROVED, REIMBURSED
- `createdAt` (DateTime): Creation timestamp

---

### Audit & Logging

#### `AuditLog`
Complete audit trail for compliance and debugging.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `userId` (String): User who made change
- `action` (AuditAction): Action type
- `entityType` (String): Entity type modified
- `entityId` (String): Entity ID modified
- `oldValue` (String): Previous value (JSON)
- `newValue` (String): New value (JSON)
- `ipAddress` (String): User IP address
- `userAgent` (String): Browser user agent
- `createdAt` (DateTime): Timestamp

**Actions:**
CREATE, UPDATE, DELETE, VIEW, EXPORT, IMPORT, LOGIN, LOGOUT

---

#### `ActivityLog`
User activity logging for analytics and monitoring.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `userId` (String): User
- `activityType` (String): Activity type
- `description` (String): Activity description
- `metadata` (String): Additional data (JSON)
- `createdAt` (DateTime): Timestamp

---

### Integrations & Notifications

#### `Integration`
External system integrations.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `type` (IntegrationType): Integration type
- `status` (IntegrationStatus): Status
- `apiKey` (String): API key (encrypted)
- `apiSecret` (String): API secret (encrypted)
- `webhookUrl` (String): Webhook URL
- `webhookSecret` (String): Webhook secret
- `lastSyncDate` (DateTime): Last sync timestamp
- `lastErrorDate` (DateTime): Last error timestamp
- `lastErrorMessage` (String): Error message
- `configuration` (String): Custom config (JSON)
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

---

#### `Notification`
User and organization notifications.

**Fields:**
- `id` (String): Unique identifier
- `userId` (String): Recipient user (optional)
- `organizationId` (String): Organization (optional)
- `title` (String): Notification title
- `message` (String): Notification message
- `type` (NotificationType): Notification type
- `status` (NotificationStatus): Send status
- `isRead` (Boolean): Read status
- `readAt` (DateTime): Read timestamp
- `actionUrl` (String): Action link
- `metadata` (String): Additional data (JSON)
- `createdAt` (DateTime): Creation timestamp
- `expiresAt` (DateTime): Expiration timestamp

---

#### `EmailTemplate`
Email templates for system communications.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `templateType` (String): INVOICE, REMINDER, RECEIPT, APPOINTMENT, etc.
- `subject` (String): Email subject
- `htmlContent` (String): HTML body
- `plainTextContent` (String): Plain text body
- `variables` (String[]): Template variables
- `isActive` (Boolean): Active template
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

---

### Analytics & Reporting

#### `Report`
Generated and scheduled reports.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `reportType` (String): REVENUE, EXPENSES, SALES, INVENTORY, PAYROLL, etc.
- `name` (String): Report name
- `description` (String): Report description
- `filters` (String): Filter criteria (JSON)
- `fileUrl` (String): Generated file URL
- `generatedDate` (DateTime): Generation timestamp
- `isScheduled` (Boolean): Scheduled report
- `scheduleFrequency` (String): DAILY, WEEKLY, MONTHLY
- `createdAt` (DateTime): Creation timestamp

---

#### `Dashboard`
User dashboard configurations.

**Fields:**
- `id` (String): Unique identifier
- `organizationId` (String): Parent organization
- `userId` (String): Owner user
- `name` (String): Dashboard name
- `layout` (String): Widget configuration (JSON)
- `isDefault` (Boolean): Default dashboard
- `isPublic` (Boolean): Public/shared dashboard
- `createdAt` (DateTime): Creation timestamp
- `updatedAt` (DateTime): Last update timestamp

---

## Relationships

### Key Relationship Patterns

**One-to-Many** (Most common):
- Organization → Users
- Organization → Customers
- Organization → Employees
- Customer → Vehicles
- Vehicle → ServiceJobs
- Invoice → Payments

**One-to-One**:
- User ↔ Employee
- User ↔ UserPreferences
- ServiceJob ↔ Quote (unique relationship)

**Many-to-Many** (via junction tables):
- Employee ↔ Skills (via EmployeeSkill)
- Part ↔ Suppliers (via SupplierPart)

### Cascade Behavior

All child relationships use `onDelete: Cascade` to ensure:
- Deleting an organization deletes all related data
- Deleting a customer deletes their vehicles and jobs
- Deleting an employee deletes their timesheets and payroll

### Query Optimization

Strategic indexes on:
- `organizationId` (all models) - Multi-tenant queries
- `status` fields - Status filtering
- Date fields - Time-range queries
- Unique fields - Fast lookups
- Foreign keys - Join optimization

---

## Setup Instructions

### Prerequisites
- PostgreSQL 12+ database
- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Install ts-node for seed script
npm install --save-dev ts-node

# Set up environment variables
cp .env.example .env
# Edit .env with your database URL
```

### Database Setup

```bash
# Generate Prisma client
npm run db:generate

# Push schema to database (creates schema)
npm run db:push

# Or run migrations (if migrations exist)
npm run db:migrate
```

### Seed Demo Data

```bash
# Run seed script to populate demo data
npm run db:seed

# Or use Prisma's built-in seed
npm run db:reset
```

### Access Database UI

```bash
# Open Prisma Studio for visual database management
npm run db:studio
```

---

## Seed Data

The seed script (`prisma/seed.ts`) creates demo data including:
- 2 sample organizations
- 2 admin users
- 3 customers
- 2 vehicles
- 2 parts
- 2 employees
- 1 quote
- 1 invoice
- 1 service job
- 1 payment
- 1 supplier
- 1 purchase order

This provides a complete working example of all system functionality.

---

## Best Practices

### 1. Multi-Tenancy Queries
Always filter by `organizationId`:
```typescript
const customers = await prisma.customer.findMany({
  where: { organizationId }
});
```

### 2. Soft Deletes
Use `deletedAt` for logical deletion:
```typescript
// Delete
await prisma.customer.update({
  where: { id },
  data: { deletedAt: new Date() }
});

// Query active records only
const customers = await prisma.customer.findMany({
  where: { deletedAt: null }
});
```

### 3. Data Validation
- Email uniqueness: `@@unique([organizationId, email])`
- Phone number format validation at application level
- Currency/decimal precision: Use `Float` with careful rounding

### 4. Performance
- Use select to limit fields returned
- Index frequently filtered fields
- Use pagination for large result sets
- Consider read replicas for heavy queries

### 5. Security
- Encrypt sensitive data (SSN, bank accounts)
- Hash passwords before storage
- Use parameterized queries
- Implement row-level security in application

### 6. Backup & Recovery
- Regular automated backups
- Test restore procedures
- Archive old payroll/audit logs
- Maintain audit trail for compliance

---

## Version History

**v1.0.0** (November 2024)
- Initial schema creation
- 60+ data models
- 8 functional modules
- Multi-tenant architecture
- Complete audit trail support

---

## Support & Questions

For questions about the schema, refer to:
- Prisma Documentation: https://www.prisma.io/docs/
- Database Design: Review entity relationships in this document
- Code Generation: Run `npm run db:generate` to create TypeScript types
