import { BankStatementImportLogColumnMap } from './BankStatementImportLogColumnMap'

export interface BankStatementImportLog {
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
	/**	Bank Account : Link - Bank Account	*/
	bank_account: string
	/**	File : Attach	*/
	file: string
	/**	Status : Select	*/
	status?: "Not Started" | "Completed"
	/**	Currency : Link - Currency	*/
	currency?: string
	/**	Number of Transactions : Int	*/
	number_of_transactions?: number
	/**	Start Date : Date	*/
	start_date?: string
	/**	End Date : Date	*/
	end_date?: string
	/**	Closing Balance : Currency	*/
	closing_balance?: number
	/**	Total Debits : Currency	*/
	total_debits?: number
	/**	Total Credits : Currency	*/
	total_credits?: number
	/**	Total Debit Transactions : Int	*/
	total_debit_transactions?: number
	/**	Total Credit Transactions : Int	*/
	total_credit_transactions?: number
	/**	Detected Date Format : Data	*/
	detected_date_format?: string
	/**	Detected Amount Format : Select	*/
	detected_amount_format?: "Separate columns for withdrawal and deposit" | "Amount column has \"CR\"/\"DR\" values" | "Amount column has positive/negative values" | "Transaction type column has \"CR\"/\"DR\" values" | "Transaction type column has \"Deposit\"/\"Withdrawal\" values" | "Transaction type column has \"C\"/\"D\" values"
	/**	Detected Header Index : Int	*/
	detected_header_index?: number
	/**	Detected Transaction Starting Index : Int	*/
	detected_transaction_starting_index?: number
	/**	Detected Transaction Ending Index : Int	*/
	detected_transaction_ending_index?: number
	/**	Column Mapping : Table - Bank Statement Import Log Column Map	*/
	column_mapping?: BankStatementImportLogColumnMap[]
	/**	PDF Tables : JSON - Per-table extraction data for PDF statements	*/
	pdf_tables?: string
}