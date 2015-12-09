<h1>Accounting for Projects</h1>

Accounting for the projects is tracked via Cost Center in ERPNext. This will require you creating separate Cost Center for each Project. Separate Cost Center for each Project all allow:<

- Allocating budget against specific Cost Center.
- Getting Profitability Report for each Project.

Let's check steps on how Project and Cost Center should be linked, and used in the sales and purchase transactions.

### 1. Linking Project and Cost Center

#### 1.1 Create Project

You should first create new Project from:

`Projects > Project > New`

In the Project, you will find field to set default Cost Center for this Project.

#### 1.2 Create Cost Center

Since budgeting and costing for each Project will be managed separately, you should create separate Cost Center for each Project.

To create new Cost Center, go to:

`Accounts > Setup > Cost Center`

[Click here to learn on how to add new Cost Center](https://erpnext.com/user-guide/accounts/cost-centers-and-budgeting).

#### 1.3 Update Cost Center in the Project

After creating Cost Center, come back to Project master, and select Cost Center creating for this Project under Default Cost Center field.

![Project Default Cost Center]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-26 at 3.52.10 pm.png)

With this, you will have Cost Center being fetched automatically in the Sales and Purchase transactions based on selection of Cost Center.

Let's check how this setting will affect your sales and purchase entries.

### 2. Selecting Project and Cost Center in the Sales and Purchase Transactions

#### 2.1 Selecting Project in the Sales Transactions

In the sales transactions (which are Sales Order, Delivery Note and Sales Invoice), Project will be selected in the More Info section. On selection of a Project, respective Cost Center will be updated for all the items in that transaction.

![Cost Center in Sales]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-26 at 3.58.45 pm.png)

#### 2.2 Selecting Project in the Purchase Cycle Transactions

In the purchase transactions, Project will be define for each item. This is because you can create a consolidated purchase entry of materials for various projects. Just like it works in sales cycle, same way in the purchase transactions, on selection of Project, its default cost center will be fetched automatically.

![Cost Center in Purchase]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-26 at 4.20.30 pm.png)

### 3. Accounting Report for a Project

#### 3.1 Projectwise Profitability

Since Project's Cost Center has been updated in both sales and purchase entries made for a specific transaction, system will provide you a projectwise profitability report. Profitability for a Project will be derived based on total value income booked minus total value of expense booked where common Cost Center (of a Project) is tagged.

![Financial Analytics for a Project]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-26 at 4.10.37 pm.png)

#### 3.2 Projectwise Budgeting

If you have also define budgets in the Cost Center of a Project, you will get Budget Variance Report for a Cost Center of a Project.

To check Budget Variance report, go to:

`Accounts > Standard Reports > Budget Variance Report`

[Click here for detailed help on how to do budgeting from Cost Center](https://erpnext.com/user-guide/accounts/budgeting).

<!-- markdown -->
