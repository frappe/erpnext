---
{
	"_label": "Accounting Setup",
	"_title_image": "img/setup-accounting.png"
}
---
## Chart of Accounts

The Chart of Accounts forms the blueprint of your organization. The overall structure of your Chart of Accounts is based on a system of double entry accounting that has become a standard all over the world to quantify how a company is doing financially. 

The Chart of Accounts helps you answer:

- What is your organization worth?
- How much debt have you taken?
- How much profit you are making (and hence paying tax)?
- How much is are you selling?
- How are your expenses broken up?

As you can see, it is very valuable to you as a business manager to see how well your business is doing. 

> Tip: If you can’t read a Balance Sheet (I confess it took me a long time to figure this out) its a good opportunity to start learning about this. It will be worth the effort. You can also take the help of your accountant to setup your Chart of Accounts.

To edit your Chart of Accounts in ERPNext go to:

> Accounts  > Chart of Accounts 

Chart of Accounts is a tree view of the names of the Accounts  (Ledgers and Groups) that a Company requires to manage its books of accounts. ERPNext sets up a simple chart of accounts for each Company you create, but you have to modify it according to your needs and legal requirements.
￼
For each company, Chart of Accounts signifies the way to classify the accounting entries, mostly based on statutory (tax, compliance to government regulations) requirements.

Let us understand the main groups of the Chart of Accounts.

### Balance Sheet Accounts

The Balance Sheet has Application of Funds (Assets) and Sources of Funds (Liabilities) that signify the net-worth of your company at any given time. When you begin or end a financial period, all the Assets are equal to the Liabilities.

> Accounting: If you are new to accounting, you might be wondering, how can Assets be equal to Liabilities? That would mean the company has nothing of its own. Thats right. All the “investment” made in the company to buy assets (like land, furniture, machines) is made by the owners and is a liability to the company. If the company would to shut down, it would need to sell all the assets and pay back all the liabilities (including profits) to the owners, leaving itself with nothing.

All the accounts under this represent an asset owned by company like "Bank Account", "Land and Property", "Furniture" or a liability (funds that the company owes to others) like "Owners funds", "Debt" etc.

Two special accounts to note here are Accounts Receivable (money you have to collect from your customers) and Accounts Payable (money you have to pay to your suppliers) under Assets and Liabilities respectively.

### Profit and Loss Accounts

Profit and Loss is the group of Income and Expense accounts that represent your accounting transactions over a period.

Unlike Balance sheet accounts, Profit and Loss accounts (or PL accounts) do not represent net worth (assets), but rather the amount of money spent and collected in servicing customers during the period. Hence at the beginning and end of your Fiscal Year, they become zero.

(On the first day of the year you have not made any profit or loss, but you still have assets, hence balance sheet accounts never become zero at the beginning or end of a period)

### Groups and Ledgers

There are two main kinds of Accounts in ERPNext - Group and Ledger. Groups can have sub-groups and ledgers within them, whereas ledgers are the leaf nodes of your chart and cannot be further classified.

Accounting Transactions can only be made against Ledger Accounts (not Groups)

> Info: The term "Ledger" means a page in an accounting book where entries are made. There is usually one ledger for each account (like a Customer or a Supplier).

> Note: An Account “Ledger” is also sometimes called as Account “Head”.

### Other Account Types

In ERPNext, you can also specify more information when you create a new Account, this is there to help you select that particular account in a scenario like Bank Account or a Tax Account and has no affect on the Chart itself.

You can also tag if an account represents a Customer, Supplier or Employee in "Master Type".

### Creating / Editing Accounts

To create new Accounts, explore your Chart of Accounts and click on an Account group under which you want to create the new Account. On the right side, you will see a options to “Edit” or “Add” a new Account.

Option to create will only appear if you click on a Group (folder) type Account.

ERPNext creates a standard structure for you when the Company is created but it is up to you to modify or add or remove accounts.

Typically, you might want to create Accounts for

- Types of Expenses (travel, salaries, telephone etc) under Expenses.
- Taxes (VAT, Sales Tax etc based on your country) under Current Liabilities.
- Types of Sales (for example, Product Sales, Service Sales etc.) under Income.
- Types of Assets (building, machinery, furniture etc.) under Fixed Assets.

---

## Chart of Cost Centers

Your Chart of Accounts is mainly for reporting your information for governmental purposes and less for how you business actually performs. Though you can tweak it a bit to resemble your business.
￼
Most businesses have multiple activities like different product lines, market segments, areas of business that share some common overheads but should ideally have their own structure to report whether they are profitable or not. For this purpose, there is an alternate structure, called the Chart of Cost Centers.

You can create a tree of Cost Centers to represent your business better. Each Income / Expense entry is also tagged against a Cost Center. 

For example, if you have two types of sales:

- Walk-in Sales
- Online Sales

You may not have shipping expenses for your walk-in customers, and no shop-rent for your online customers. If you want to get the profitability of each of these separately, you create the two as Cost Centers and you can mark all sales as either "Walk-in" or "Online" and also all your purchases in the same way.

So when you do your analysis you can get a better idea which side of your business is doing better.  Since ERPNext has option to add multiple Companies, you can create Cost Centers for each Company and manage it separately.

To setup your Chart of Cost Centers go to:

> Accounts > Chart of Cost Centers

Cost centers help you in one more activity, budgeting.

### Budgeting

ERPNext will help you set and manage budgets on your Cost Centers. This is useful when, for example, you are doing online sales and you have a budget for search ads and you want ERPNext to stop or warn you from over spending based on that budget. 

Budgets are also great for planning purposes. When you are making your plans for the next financial year, you would typically target a revenue and based on that you would set your expenses. Setting a budget will ensure that your expenses do not get out of hand at any point based on your plans.

You can define it in the Cost Center. If you have seasonal sales you can also define a budget distribution that the budget will follow.
￼
#### Budget Actions

ERPNext allows you to either:

- Stop.
- Warn or, 
- Ignore 

if you exceed budgets. 

These can be defined from the Company record.

Even if you choose to “ignore” budget overruns, you will get a wealth of information from the “Budget vs Actual” variance report.

> Note: When you set a budget, it has to be set per Account under the Cost Center. For example if you have a Cost Center “Online Sales”, you can restrict “Advertising Budget” by creating a row with that Account and defining the amount.