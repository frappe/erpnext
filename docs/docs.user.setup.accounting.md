---
{
	"_label": "Chart of Accounts",
	"_icon": "sitemap",
	"_links": [
		"docs.user.accounts"
	]
}
---
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

> [Accounts](docs.user.accounts.html)  > Chart of Accounts 

Chart of Accounts is a tree view of the names of the Accounts  (Ledgers and Groups) that a Company requires to manage its books of accounts. ERPNext sets up a simple chart of accounts for each Company you create, but you have to modify it according to your needs and legal requirements.
￼
For each company, Chart of Accounts signifies the way to classify the accounting entries, mostly based on statutory (tax, compliance to government regulations) requirements.

Let us understand the main groups of the Chart of Accounts.

![Chart of Accounts: Root Accounts](img/chart-of-accounts.png)

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

![Chart of Accounts: Groups and Ledger](img/chart-of-accounts-1.png)

### Other Account Types

In ERPNext, you can also specify more information when you create a new Account, this is there to help you select that particular account in a scenario like Bank Account or a Tax Account and has no affect on the Chart itself.

You can also tag if an account represents a Customer, Supplier or Employee in "Master Type".

### Creating / Editing Accounts

To create new Accounts, explore your Chart of Accounts and click on an Account group under which you want to create the new Account. On the right side, you will see a options to “Edit” or “Add” a new Account.

![Chart of Accounts: New Account](img/chart-of-accounts-2.png)

Option to create will only appear if you click on a Group (folder) type Account.

ERPNext creates a standard structure for you when the Company is created but it is up to you to modify or add or remove accounts.

Typically, you might want to create Accounts for

- Types of Expenses (travel, salaries, telephone etc) under Expenses.
- Taxes (VAT, Sales Tax etc based on your country) under Current Liabilities.
- Types of Sales (for example, Product Sales, Service Sales etc.) under Income.
- Types of Assets (building, machinery, furniture etc.) under Fixed Assets.
