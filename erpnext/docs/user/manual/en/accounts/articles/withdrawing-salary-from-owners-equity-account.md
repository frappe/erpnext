#Withdrawing Salary from Owner's Equity Account

### Question

After meeting with my accountant here in the US, I was informed that with my company being a sole member, I should not pay myself a salary that would hit the direct expenses account but instead should take a "draw" that hits the balance sheet and not the expenses. Can you please advise how I should set this up in ERP Next please?

### Answer

1. Create an account for **Owner's Equity** under Liabilities if you already do not have. This account will be your investment in the business and the accumulated profits (or losses). It will have a "Credit" type balance.
2. In an Version 5, Equity will be a new head (not under Liabilities). (In either case Assets = Owner's Equity + Liabilities, so your balance sheet will be okay [Learn more about owner's equity account](http://www.accountingcoach.com/blog/what-is-owners-equity)).
3. Create an account for **Owner's Draws** under **Owner's Equity**.
4. Note that the balance of **Owner's Draws** will always be negative since you are reducing money from your total equity / profits.

### Example

Example journal entry (using Journal Voucher in ERPNext) for a withdrawal of $1000 would be:

1. Credit **Cash** $1000
2. Debit **Owner's Draws** $1000

<!-- markdown -->
