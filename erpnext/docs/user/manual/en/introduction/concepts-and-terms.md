# Concepts And Terms

Before you start implementation, lets get familiar with the terminology that
is used and some basic concepts in ERPNext.

* * *

### Basic Concepts

#### Company

This represents the Company records for which ERPNext is setup. With this same
setup, you can create multiple Company records, each representing a different
legal entity. The accounting for each Company will be different, but they will
share the Customer, Supplier and Item records.

> Setup > Company

#### Customer

Represents a customer. A Customer can be an individual or an organization.
You can create multiple Contacts and Addresses for each Customer.

> Selling > Customer

#### Supplier

Represents a supplier of goods or services. Your telephone company is a
Supplier, so is your raw materials Supplier. Again, a Supplier can be an
individual or an organization and has multiple Contacts and Addresses.

> Buying > Supplier

#### Item

A Product, sub-product or Service that is either bought, sold or manufactured
and is uniquely identified.

> Stock > Item

#### Account

An Account is a heading under which financial and business transactions are
carried on. For example, “Travel Expense” is an account, “Customer Zoe”,
“Supplier Mae” are accounts. ERPNext creates accounts for Customers and
Suppliers automatically.

> Accounts > Chart of Accounts

#### Address

An address represents location details of a Customer or Supplier. These can be
of different locations such as Head Office, Factory, Warehouse, Shop etc.

> Selling > Address

#### Contact

An individual Contact belongs to a Customer or Supplier or is just an
independent. A Contact has a name and contact details like email and phone
number.

> Selling > Contact

#### Communication

A list of all Communication with a Contact or Lead. All emails sent from the
system are added to the Communication table.

> Support > Communication

#### Price List

A Price List is a place where different rate plans can be stored. It’s a name
you give to a set of Item Prices stored under a particular List.

> Selling > Price List


> Buying > Price List

* * *

### Accounting

#### Fiscal Year

Represents a Financial Year or Accounting Year. You can operate multiple
Fiscal Years at the same time. Each Fiscal Year has a start date and an end
date and transactions can only be recorded in this period. When you “close” a
fiscal year, it's balances are transferred as “opening” balances for the next
fiscal year.

> Setup > Company > Fiscal Year

#### Cost Center

A Cost Center is like an Account, but the only difference is that its
structure represents your business more closely than Accounts.
For example, in your Chart of Accounts, you can separate your expenses by its type 
(i.e., travel, marketing, etc.). In your Chart of Cost Centers, you can separate 
them by product line or business group (e.g., online sales, retail sales, etc.).

> Accounts > Chart of Cost Centers

#### Journal Entry

A document that contains General Ledger (GL) entries and the sum of Debits and
Credits of those entries is the same. In ERPNext you can update Payments,
Returns, etc., using Journal Entries.

> Accounts > Journal Entry

#### Sales Invoice

A bill sent to Customers for delivery of Items (goods or services).

> Accounts > Sales Invoice

#### Purchase Invoice

A bill sent by a Supplier for delivery of Items (goods or services).

> Accounts > Purchase Invoice

#### Currency

ERPNext allows you to book transactions in multiple currencies. There is only
one currency for your book of accounts though. While posting your Invoices with
payments in different currencies, the amount is converted to the default
currency by the specified conversion rate.

> Setup > Currency

* * *

### Selling

#### Customer Group

A classification of Customers, usually based on market segment.

> Selling > Setup > Customer Group

#### Lead

A person who could be a future source of business. A Lead may generate
Opportunities. (from: “may lead to a sale”).

> CRM > Lead

#### Opportunity

A potential sale. (from: “opportunity for a business”).

> CRM > Opportunity

#### Quotation

Customer's request to price an item or service.

> Selling > Quotation

#### Sales Order

A note confirming the terms of delivery and price of an Item (product or
service) by the Customer. Deliveries, Production Orders and Invoices are made
on basis of Sales Orders.

> Selling > Sales Order

#### Territory

A geographical area classification for sales management. You can set targets
for Territories and each sale is linked to a Territory.

> Selling > Setup > Territory

#### Sales Partner

A third party distributer / dealer / affiliate / commission agent who sells
the company’s products usually for a commission.

> Selling > Setup > Sales Partner

#### Sales Person

Someone who pitches to the Customer and closes deals. You can set targets for
Sales Persons and tag them in transactions.

> Selling > Setup > Sales Person

* * *

### Buying

#### Purchase Order

A contract given to a Supplier to deliver the specified Items at the specified
cost, quantity, dates and other terms.

> Buying > Purchase Order

#### Material Request

A request made by a system User, or automatically generated by ERPNext based
on reorder level or projected quantity in Production Plan for purchasing a set
of Items.

> Buying > Material Request

* * *

### Stock (Inventory)

#### Warehouse

A logical Warehouse against which stock entries are made.

> Stock > Warehouse

#### Stock Entry

Material transfer from a Warehouse, to a Warehouse or from one Warehouse to
another.

> Stock > Stock Entry

#### Delivery Note

A list of Items with quantities for shipment. A Delivery Note will reduce the
stock of Items for the Warehouse from where you ship. A Delivery Note is
usually made against a Sales Order.

> Stock > Delivery Note

#### Purchase Receipt

A note stating that a particular set of Items were received from the Supplier,
most likely against a Purchase Order.

> Stock > Purchase Receipt

#### Serial Number

A unique number given to a particular unit of an Item.

> Stock > Serial Number

#### Batch

A number given to a group of units of a particular Item that may be purchased
or manufactured in a group.

> Stock > Batch

#### Stock Ledger Entry

A unified table for all material movement from one warehouse to another. This
is the table that is updated when a Stock Entry, Delivery Note, Purchase
Receipt, and Sales Invoice (POS) is made.

#### Stock Reconciliation

Update Stock of multiple Items from a spreadsheet (CSV) file.

> Stock > Stock Reconciliation

#### Quality Inspection

A note prepared to record certain parameters of an Item at the time of Receipt
from Supplier, or Delivery to Customer.

> Stock > Quality Inspection

#### Item Group

A classification of Item.

> Stock > Setup > Item Group

* * *

### Human Resource Management

#### Employee

Record of a person who has been in present or past, in the employment of the
company.

> Human Resources > Employee

#### Leave Application

A record of an approved or rejected request for leave.

> Human Resource > Leave Application

#### Leave Type

A type of leave (e.g., Sick Leave, Maternity Leave, etc.).

> Human Resource > Leave and Attendance > Leave Type

#### Process Payroll

A tool that helps in creation of multiple Salary Slips for Employees.

> Human Resource > Salary and Payroll > Process Payroll

#### Salary Slip

A record of the monthly salary given to an Employee.

> Human Resource > Salary Slip

#### Salary Structure

A template identifying all the components of an Employees' salary (earnings), 
tax and other social security deductions.

> Human Resource > Salary and Payroll > Salary Structure

#### Appraisal

A record of the performance of an Employee over a specified period based on
certain parameters.

> Human Resources > Appraisal

#### Appraisal Template

A template recording the different parameters of an Employees' performance and
their weightage for a particular role.

> Human Resources > Employee Setup > Appraisal Template

#### Attendance

A record indicating presence or absence of an Employee on a particular day.

> Human Resources > Attendance

* * *

### Manufacturing

#### Bill of Materials (BOM)

A list of Operations and Items with their quantities, that are required to
produce another Item. A Bill of Materials (BOM) is used to plan purchases and
do product costing.

> Manufacturing > BOM

#### Workstation

A place where a BOM operation takes place. It is useful to calculate the
direct cost of the product.

> Manufacturing > Workstation

#### Production Order

A document signaling production (manufacture) of a particular Item with
specified quantities.

> Manufacturing > Production Order

#### Production Planning Tool

A tool for automatic creation of Production Orders and Purchase Requests based
on Open Sales Orders in a given period.

> Manufacturing > Production Planning Tool

* * *

### Website

#### Blog Post

A short article that appears in the “Blog” section of the website generated
from the ERPNext website module. Blog is a short form of “Web Log”.

> Website > Blog Post

#### Web Page

A web page with a unique URL (web address) on the website generated from
ERPNext.

> Website > Web Page

* * *

### Setup / Customization

#### Custom Field

A user defined field on a form / table.

> Setup > Customize ERPNext > Custom Field

#### Global Defaults

This is the section where you set default values for various parameters of the
system.

> Setup > Data > Global Defaults

#### Print Heading

A title that can be set on a transaction just for printing. For example, you
want to print a Quotation with a title “Proposal” or “Pro forma Invoice”.

> Setup > Branding and Printing > Print Headings

#### Terms and Conditions

Text of your terms of contract.

> Selling > Setup > Terms and Conditions

#### Unit of Measure (UOM)

How quantity is measured for an Item. E.g., Kg, No., Pair, Packet, etc.

> Stock > Setup > UOM

{next}
