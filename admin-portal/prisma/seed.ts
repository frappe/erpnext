import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('Starting database seeding...');

  // Clear existing data (optional - only for development)
  // await prisma.$executeRawUnsafe('TRUNCATE TABLE "User" CASCADE');

  // ============================================================================
  // CREATE ORGANIZATIONS
  // ============================================================================
  console.log('Creating organizations...');

  const org1 = await prisma.organization.create({
    data: {
      name: 'AutoCRM Pro - Demo Shop',
      type: 'INDEPENDENT_SHOP',
      email: 'demo@autocrm.com',
      phone: '(555) 123-4567',
      website: 'https://autocrm-demo.com',
      addressLine1: '123 Main Street',
      city: 'San Francisco',
      state: 'CA',
      postalCode: '94102',
      country: 'USA',
      timezone: 'America/Los_Angeles',
      currency: 'USD',
    },
  });

  const org2 = await prisma.organization.create({
    data: {
      name: 'Multi-Location Motors',
      type: 'MULTI_LOCATION',
      email: 'contact@multimotor.com',
      phone: '(555) 234-5678',
      website: 'https://multimotor.com',
      addressLine1: '456 Oak Avenue',
      city: 'Los Angeles',
      state: 'CA',
      postalCode: '90001',
      country: 'USA',
      timezone: 'America/Los_Angeles',
      currency: 'USD',
    },
  });

  // ============================================================================
  // CREATE ADMIN USERS
  // ============================================================================
  console.log('Creating admin users...');

  const adminUser1 = await prisma.user.create({
    data: {
      organizationId: org1.id,
      email: 'admin@autocrm.com',
      firstName: 'John',
      lastName: 'Admin',
      role: 'ADMIN',
      status: 'ACTIVE',
      passwordHash: 'hashed_password_1',
      emailVerified: true,
      emailVerifiedAt: new Date(),
    },
  });

  const adminUser2 = await prisma.user.create({
    data: {
      organizationId: org2.id,
      email: 'admin@multimotor.com',
      firstName: 'Jane',
      lastName: 'Manager',
      role: 'MANAGER',
      status: 'ACTIVE',
      passwordHash: 'hashed_password_2',
      emailVerified: true,
      emailVerifiedAt: new Date(),
    },
  });

  // ============================================================================
  // CREATE CUSTOMERS
  // ============================================================================
  console.log('Creating customers...');

  const customer1 = await prisma.customer.create({
    data: {
      organizationId: org1.id,
      firstName: 'Alice',
      lastName: 'Johnson',
      email: 'alice.johnson@email.com',
      phoneNumber: '(555) 111-0001',
      type: 'INDIVIDUAL',
      status: 'ACTIVE',
      addressLine1: '789 Elm Street',
      city: 'San Francisco',
      state: 'CA',
      postalCode: '94103',
      loyaltyPoints: 250,
    },
  });

  const customer2 = await prisma.customer.create({
    data: {
      organizationId: org1.id,
      firstName: 'Bob',
      lastName: 'Smith',
      email: 'bob.smith@email.com',
      phoneNumber: '(555) 111-0002',
      type: 'INDIVIDUAL',
      status: 'ACTIVE',
      addressLine1: '321 Pine Road',
      city: 'Oakland',
      state: 'CA',
      postalCode: '94612',
      loyaltyPoints: 150,
    },
  });

  const customer3 = await prisma.customer.create({
    data: {
      organizationId: org2.id,
      firstName: 'Corporate',
      lastName: 'Fleet',
      email: 'fleet@corporate.com',
      phoneNumber: '(555) 222-0001',
      type: 'BUSINESS',
      status: 'ACTIVE',
      addressLine1: '999 Industrial Way',
      city: 'Los Angeles',
      state: 'CA',
      postalCode: '90002',
      loyaltyPoints: 500,
    },
  });

  // ============================================================================
  // CREATE VEHICLES
  // ============================================================================
  console.log('Creating vehicles...');

  const vehicle1 = await prisma.vehicle.create({
    data: {
      organizationId: org1.id,
      customerId: customer1.id,
      vin: '1HGBH41JXMN109186',
      licensePlate: 'ABC123',
      year: 2022,
      make: 'Honda',
      model: 'Accord',
      trim: 'EX',
      color: 'Silver',
      mileage: 15000,
      status: 'ACTIVE',
    },
  });

  const vehicle2 = await prisma.vehicle.create({
    data: {
      organizationId: org1.id,
      customerId: customer2.id,
      vin: '2T1BURHE0JC041186',
      licensePlate: 'XYZ789',
      year: 2021,
      make: 'Toyota',
      model: 'Camry',
      trim: 'SE',
      color: 'Blue',
      mileage: 25000,
      status: 'ACTIVE',
    },
  });

  // ============================================================================
  // CREATE PARTS
  // ============================================================================
  console.log('Creating parts...');

  const part1 = await prisma.part.create({
    data: {
      organizationId: org1.id,
      partNumber: 'OIL-FILTER-001',
      name: 'Oil Filter',
      category: 'FILTERS',
      manufacturer: 'Mobil',
      costPrice: 5.99,
      sellingPrice: 12.99,
      quantity: 45,
      minimumStockLevel: 10,
      maximumStockLevel: 100,
      reorderQuantity: 25,
      status: 'ACTIVE',
    },
  });

  const part2 = await prisma.part.create({
    data: {
      organizationId: org1.id,
      partNumber: 'BRAKE-PAD-001',
      name: 'Brake Pads Set',
      category: 'BRAKES',
      manufacturer: 'Bosch',
      costPrice: 24.99,
      sellingPrice: 49.99,
      quantity: 12,
      minimumStockLevel: 5,
      maximumStockLevel: 30,
      reorderQuantity: 15,
      status: 'ACTIVE',
    },
  });

  // ============================================================================
  // CREATE EMPLOYEES
  // ============================================================================
  console.log('Creating employees...');

  const employee1 = await prisma.employee.create({
    data: {
      organizationId: org1.id,
      firstName: 'Mike',
      lastName: 'Mechanic',
      email: 'mike@autocrm.com',
      phoneNumber: '(555) 333-0001',
      role: 'MECHANIC',
      status: 'ACTIVE',
      hireDate: new Date('2022-01-15'),
      baseSalary: 55000,
      hourlyRate: 26.44,
    },
  });

  const employee2 = await prisma.employee.create({
    data: {
      organizationId: org1.id,
      firstName: 'Sarah',
      lastName: 'Advisor',
      email: 'sarah@autocrm.com',
      phoneNumber: '(555) 333-0002',
      role: 'SERVICE_ADVISOR',
      status: 'ACTIVE',
      hireDate: new Date('2022-03-01'),
      baseSalary: 45000,
      hourlyRate: 21.63,
    },
  });

  // ============================================================================
  // CREATE QUOTES
  // ============================================================================
  console.log('Creating quotes...');

  const quote1 = await prisma.quote.create({
    data: {
      organizationId: org1.id,
      customerId: customer1.id,
      vehicleId: vehicle1.id,
      quoteNumber: 'QT-2024-001',
      status: 'SENT',
      estimatedCost: 250.00,
      laborCost: 150.00,
      partsCost: 100.00,
      taxAmount: 28.00,
      grandTotal: 278.00,
      validUntil: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days from now
      description: 'Regular maintenance and oil change',
    },
  });

  // ============================================================================
  // CREATE INVOICES
  // ============================================================================
  console.log('Creating invoices...');

  const invoice1 = await prisma.invoice.create({
    data: {
      organizationId: org1.id,
      customerId: customer1.id,
      vehicleId: vehicle1.id,
      invoiceNumber: 'INV-2024-001',
      status: 'PAID',
      invoiceDate: new Date(),
      dueDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
      totalAmount: 250.00,
      taxAmount: 28.00,
      discountAmount: 0,
      grandTotal: 278.00,
      amountPaid: 278.00,
      amountDue: 0,
    },
  });

  // ============================================================================
  // CREATE SERVICE JOBS
  // ============================================================================
  console.log('Creating service jobs...');

  const serviceJob1 = await prisma.serviceJob.create({
    data: {
      organizationId: org1.id,
      customerId: customer1.id,
      vehicleId: vehicle1.id,
      jobNumber: 'JOB-2024-001',
      jobType: 'MAINTENANCE',
      status: 'IN_PROGRESS',
      priority: 'MEDIUM',
      estimatedCost: 250.00,
      actualCost: 0,
      laborCost: 150.00,
      partsCost: 100.00,
      description: 'Regular maintenance and inspection',
      assignedMechanicId: employee1.id,
    },
  });

  // ============================================================================
  // CREATE PAYMENTS
  // ============================================================================
  console.log('Creating payments...');

  const payment1 = await prisma.payment.create({
    data: {
      organizationId: org1.id,
      invoiceId: invoice1.id,
      paymentMethod: 'CREDIT_CARD',
      amount: 278.00,
      status: 'COMPLETED',
      paymentDate: new Date(),
      transactionId: 'TXN-2024-001',
    },
  });

  // ============================================================================
  // CREATE SUPPLIER
  // ============================================================================
  console.log('Creating suppliers...');

  const supplier1 = await prisma.supplier.create({
    data: {
      organizationId: org1.id,
      supplierName: 'AutoParts Direct',
      contactPerson: 'John Supplier',
      email: 'contact@autopartsdirect.com',
      phoneNumber: '(555) 444-0001',
      addressLine1: '555 Supply Road',
      city: 'San Jose',
      state: 'CA',
      postalCode: '95110',
      paymentTerms: 'NET_30',
      leadTimeDays: 3,
      rating: 4.5,
    },
  });

  // ============================================================================
  // CREATE PURCHASE ORDER
  // ============================================================================
  console.log('Creating purchase orders...');

  const purchaseOrder1 = await prisma.purchaseOrder.create({
    data: {
      organizationId: org1.id,
      supplierId: supplier1.id,
      poNumber: 'PO-2024-001',
      status: 'PENDING',
      orderDate: new Date(),
      expectedDeliveryDate: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000), // 3 days from now
      totalAmount: 149.75,
      taxAmount: 13.48,
      shippingCost: 10.00,
      discountAmount: 0,
      grandTotal: 173.23,
    },
  });

  // ============================================================================
  // CREATE LOCATION
  // ============================================================================
  console.log('Creating locations...');

  const location1 = await prisma.location.create({
    data: {
      organizationId: org1.id,
      name: 'Main Workshop',
      addressLine1: '123 Main Street',
      city: 'San Francisco',
      state: 'CA',
      postalCode: '94102',
      phone: '(555) 123-4567',
      email: 'main@autocrm.com',
      isMainLocation: true,
    },
  });

  // ============================================================================
  // CREATE MAINTENANCE PLAN
  // ============================================================================
  console.log('Creating maintenance plans...');

  const maintenancePlan1 = await prisma.maintenancePlan.create({
    data: {
      organizationId: org1.id,
      vehicleId: vehicle1.id,
      planName: 'Standard Maintenance Plan',
      status: 'ACTIVE',
      isRecurring: true,
      recurrenceInterval: 6, // Every 6 months
      recurrenceMileage: 5000,
    },
  });

  // ============================================================================
  // CREATE NOTIFICATIONS
  // ============================================================================
  console.log('Creating notifications...');

  const notification1 = await prisma.notification.create({
    data: {
      organizationId: org1.id,
      userId: adminUser1.id,
      type: 'JOB_REMINDER',
      title: 'Service Job Reminder',
      message: 'Service job JOB-2024-001 is in progress and due soon',
      status: 'SENT',
    },
  });

  // ============================================================================
  // SUMMARY
  // ============================================================================
  console.log('✅ Database seeding completed successfully!');
  console.log(`
Organization 1: ${org1.name} (${org1.id})
Organization 2: ${org2.name} (${org2.id})
Admin User 1: ${adminUser1.email}
Admin User 2: ${adminUser2.email}
Customers Created: 3
Vehicles Created: 2
Parts Created: 2
Employees Created: 2
Quotes Created: 1
Invoices Created: 1
Service Jobs Created: 1
Payments Created: 1
  `);
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error('❌ Seeding failed:', e);
    await prisma.$disconnect();
    process.exit(1);
  });
