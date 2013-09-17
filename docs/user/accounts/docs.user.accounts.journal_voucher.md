---
{
	"_label": "Journal Vouchers"
}
---
All types of accounting entries other than **Sales Invoice** and **Purchase Invoice** are made using the **Journal Voucher**. A **Journal Voucher** (also called Journal Entry) is a standard accounting transaction that affects multiple Accounts and the sum of debits is equal to the sum of credits.

To create a Journal Voucher go to:

> Accounts > Journal Voucher > New Journal Voucher



![Journal Voucher](img/journal-voucher.png)




In a Journal Voucher, you must select.

- Type of Voucher from the drop down. 
- Add rows for the individual accounting entries. In each row, you must specify:
	- The Account that will be affected
	- The amount to Debit or Credit
	- The Cost Center (if it is an Income or Expense)
	- Against Voucher: Link it to a voucher or invoice if it affects the “outstanding” amount of that invoice.
	- Is Advance: Select “Yes” if you want to make it selectable in an Invoice. 
Other information in case it is a Bank Payment or a bill.

#### Difference

The “Difference” field is the difference between the Debit and Credit amounts. This should be zero if the Journal Voucher is to be “Submitted”. If this number is not zero, you can click on “Make Difference Entry” to add a new row with the amount required to make the total as zero.

---

## Common Entries

A look at some of the common accounting entries that can be done via Journal Voucher.

#### Expenses (non accruing)

Many times it may not be necessary to accrue an expense, but it can be directly booked against an expense Account on payment. For example a travel allowance or a telephone bill. You can directly debit Telephone Expense (instead of your telephone company) and credit your Bank on payment.

- Debit: Expense Account (like Telephone expense)
- Credit: Bank or Cash Account

#### Bad Debts or Write Offs

If you are writing off an Invoice as a bad debt, you can create a Journal Voucher similar to a Payment, except instead of debiting your Bank, you can debit an Expense Account called Bad Debts.

- Debit: Bad Debts Written Off
- Credit: Customer

> Note: There may be regulations in your country before you can write off bad debts.

#### Depreciation

Depreciation is when you write off certain value of your assets as an expense. For example if you have a computer that you will use for say 5 years, you can distribute its expense over the period and pass a Journal Voucher at the end of each year reducing its value by a certain percentage.

- Debit: Depreciation (Expense)
- Credit: Asset (the Account under which you had booked the asset to be depreciated)

> Note: There may be regulations in your country that define by how much amount you can depreciate a class of Assets.
