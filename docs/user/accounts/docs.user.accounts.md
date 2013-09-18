---
{
	"_label": "Accounts",
	"_toc": [
		"docs.user.accounts.sales_invoice",
		"docs.user.accounts.purchase_invoice",
		"docs.user.accounts.payments",
		"docs.user.accounts.journal_voucher",
		"docs.user.accounts.opening_entry",
		"docs.user.accounts.closing",
		"docs.user.accounts.reports",
		"docs.user.accounts.voucher_import",
		"docs.user.accounts.pos"
	]
}
---

![Accounts](img/accounts-image.png)



At end of the sales and purchase cycle is billing and payments. You may have an accountant in your team, or you may be doing accounting yourself or you may have outsourced your accounting. Financial accounting forms the core of any business management system like an ERP.

In ERPNext, your accounting operations consists of 3 main transactions:

- Sales Invoice: The bills that you raise to your Customers for the products or services you provide. 
- Purchase Invoice: Bills that your Suppliers give you for their products or services. 
- Journal Vouchers: For accounting entries, like payments, credit and other types.

---

### Accounting Basics

#### Debit and Credit

People new to accounting are often confused with the terms Debit and Credit. Contrary to their meaning, these terms have nothing to do with who owes what. 

Debit and Credit are conventions. All accounting follows these so that it is easy to understand the state of finances in a universal manner. These conventions are:

- All Accounts are of type Debit or Credit.
- Assets and Expenses (and their sub-groups) are always Debit.
- Liabilities and Income (and their sub-groups) are always Credit.
- In all accounting entries, you “debit” an Account or “credit” one.
- When you “debit” an Debit Account (an asset or expense), its value increases (“add” operation). When you “credit” a Debit Account, its value decreases (“subtract” operation). The same rule applies for Credit Accounts. “Crediting” a Credit Account, increases its value, “debiting” it decreases its value.
- All accounting transactions (like a sales or a payment) must affect at least two different Accounts and sum of debits must be equal to sum of credits for the transaction. This is called the “double-entry bookkeeping system”.

Still confused? These conventions will become clearer as you make transactions.

#### Accrual System

Another important concept to understand in Accounting is accrual. This is important when your payment happens separately from delivery. 

For example you buy X from a Supplier and your Supplier sends you a bill and expects you to pay in, for example, seven days. Even if you have not yet paid your Supplier, your expense must be booked immediately. This expense is booked against a group of Accounts called “Accounts Payable” that is the sum of all your outstanding dues to your Suppliers. This is called accrual. When you pay your Supplier, you will cancel his dues and update your bank account.

ERPNext works on an accrual system. The transactions that accrue income and expense are Sales Invoice and Purchase Invoice.

In retail, typically, delivery and payment happens at the same time. To cover this scenario, we have in ERPNext a POS Invoice (POS = Point of Sales). More on that later.

