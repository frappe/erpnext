
export interface JournalEntryAccount{
	name: string
	creation: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Account : Link - Account	*/
	account: string
	/**	Account Type : Data	*/
	account_type?: string
	/**	Bank Account : Link - Bank Account	*/
	bank_account?: string
	/**	Party Type : Link - DocType	*/
	party_type?: string
	/**	Party : Dynamic Link	*/
	party?: string
	/**	Cost Center : Link - Cost Center - If Income or Expense	*/
	cost_center?: string
	/**	Project : Link - Project	*/
	project?: string
	/**	Account Currency : Link - Currency	*/
	account_currency?: string
	/**	Exchange Rate : Float	*/
	exchange_rate?: number
	/**	Debit : Currency	*/
	debit_in_account_currency?: number
	/**	Debit in Company Currency : Currency	*/
	debit?: number
	/**	Credit : Currency	*/
	credit_in_account_currency?: number
	/**	Credit in Company Currency : Currency	*/
	credit?: number
	/**	Reference Type : Select	*/
	reference_type?: "" | "Sales Invoice" | "Purchase Invoice" | "Journal Entry" | "Sales Order" | "Purchase Order" | "Expense Claim" | "Asset" | "Loan" | "Payroll Entry" | "Employee Advance" | "Exchange Rate Revaluation" | "Invoice Discounting" | "Fees" | "Full and Final Statement" | "Payment Entry"
	/**	Reference Name : Dynamic Link	*/
	reference_name?: string
	/**	Reference Due Date : Date	*/
	reference_due_date?: string
	/**	Reference Detail No : Data	*/
	reference_detail_no?: string
	/**	Is Advance : Select	*/
	is_advance?: "No" | "Yes"
	/**	User Remark : Small Text	*/
	user_remark?: string
	/**	Against Account : Text	*/
	against_account?: string
}