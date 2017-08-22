#Tracking Project Profibitability using Cost Center

To track expenses and profibility for a project, you can use Cost Centers. You should create separate Cost Center for each Project. This will allow you to.

- Allocating budget on expense for Projects.
- Tracking Profitability of Project.

Let's check steps on how Project and Cost Center should be linked, and used in the sales and purchase transactions.

### 1. Linking Project and Cost Center

#### 1.1 Create Project

To create new Project, go to:

`Projects > Project > New`

<img alt="Project Default Cost Center" class="screenshot" src="/docs/assets/img/articles/project-cost-center-4.png">

#### 1.2 Create Cost Center

Since budgeting and costing for each Project will be managed separately, you should create separate Cost Center for each Project.

To create new Cost Center, go to:

`Accounts > Setup > Cost Center`

[Click here to learn how to manage Cost Centers.](/docs/user/manual/en/accounts/setup/cost-center.html)

#### 1.3 Update Cost Center in the Project

Update Cost Center in the Project master.

<img alt="Project Default Cost Center" class="screenshot" src="/docs/assets/img/articles/project-cost-center-1.png">

In the sales and purchase transactions, if Project is selected, then Cost Center will fetched from the Project master.

Let's check how this setting will affect your sales and purchase entries.

### 2. Project and Cost Center in Sales & Purchase Transactions

#### 2.1 Project in the Sales Transactions

In the sales transactions (which are Sales Order, Delivery Note and Sales Invoice), Project will be selected in the More Info section. On selection of a Project, respective Cost Center will be updated for all the items in that transaction. Cost Center will be updated on in the transactions which has Cost Center field.

<img alt="Project Default Cost Center" class="screenshot" src="/docs/assets/img/articles/project-cost-center-2.png">

#### 2.2 Project in the Purchase Transactions

In the purchase transactions, Project is define for each line item. This is because you can create a consolidated purchase entry for various projects. On selection of Project, its default cost center will auto-fetch.

As per perpetual inventory valuation system, expense for the purchased item will be booked when raw-materials are consumed. On consumption of goods, if you are creating Material Issue (stock) entry, then Expense Cost (says Cost of Goods Sold) and Project's Cost Center should be updated in that entry.

<img alt="Project Default Cost Center" class="screenshot" src="/docs/assets/img/articles/project-cost-center-3.png">

### 3. Accounting Report for a Project

#### 3.1 Projectwise Profitability

Since Project's Cost Center is updated in both sales and purchase entries, you can check Project Profitability based on report on Cost Center.

**Monthly Project Analysis**

<img alt="Project Default Cost Center" class="screenshot" src="/docs/assets/img/articles/project-cost-center-5.png">

**Overall Profitability**

<img alt="Project Default Cost Center" class="screenshot" src="/docs/assets/img/articles/project-cost-center-6.png">

#### 3.2 Projectwise Budgeting

You can define budgets against the Cost Center associated with a Project. At any point of time, you can refer Budget Variance Report to analysis the expense vs budget against a cost center.

To check Budget Variance report, go to:

`Accounts > Budget and Cost Center > Budget Variance Report`

[Click here to learn how to do budgeting from Cost Center](/docs/user/manual/en/accounts/budgeting.html).

<!-- markdown -->