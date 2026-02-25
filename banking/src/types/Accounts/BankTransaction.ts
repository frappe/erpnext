import { BankTransactionPayments } from './BankTransactionPayments'

export interface BankTransaction{
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
	/**	Is Rule Evaluated : Check	*/
	is_rule_evaluated?: 0 | 1
	/**	Matched Rule : Link - Mint Bank Transaction Rule	*/
	matched_rule?: string
	/**	Series : Select	*/
	naming_series: "ACC-BTN-.YYYY.-"
	/**	Date : Date	*/
	date?: string
	/**	Status : Select	*/
	status?: "" | "Pending" | "Settled" | "Unreconciled" | "Reconciled" | "Cancelled"
	/**	Bank Account : Link - Bank Account	*/
	bank_account?: string
	/**	Company : Link - Company	*/
	company?: string
	/**	Amended From : Link - Bank Transaction	*/
	amended_from?: string
	/**	Deposit : Currency	*/
	deposit?: number
	/**	Withdrawal : Currency	*/
	withdrawal?: number
	/**	Currency : Link - Currency	*/
	currency?: string
	/**	Description : Small Text	*/
	description?: string
	/**	Reference Number : Data	*/
	reference_number?: string
	/**	Transaction ID : Data	*/
	transaction_id?: string
	/**	Transaction Type : Data	*/
	transaction_type?: string
	/**	Payment Entries : Table - Bank Transaction Payments	*/
	payment_entries?: BankTransactionPayments[]
	/**	Allocated Amount : Currency	*/
	allocated_amount?: number
	/**	Unallocated Amount : Currency	*/
	unallocated_amount?: number
	/**	Party Type : Link - DocType	*/
	party_type?: string
	/**	Party : Dynamic Link	*/
	party?: string
	/**	Party Name/Account Holder (Bank Statement) : Data	*/
	bank_party_name?: string
	/**	Party Account No. (Bank Statement) : Data	*/
	bank_party_account_number?: string
	/**	Party IBAN (Bank Statement) : Data	*/
	bank_party_iban?: string
}