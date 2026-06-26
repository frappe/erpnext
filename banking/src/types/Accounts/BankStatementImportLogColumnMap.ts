
export interface BankStatementImportLogColumnMap{
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
	/**	Header Text : Data	*/
	header_text: string
	/**	Index : Int	*/
	index: number
	/**	Maps To : Select	*/
	maps_to: "Do not import" | "Date" | "Withdrawal" | "Deposit" | "Amount" | "Description" | "Reference" | "Transaction Type" | "Debit/Credit" | "Balance" | "Included Fee" | "Excluded Fee" | "Party Name/Account Holder" | "Party Account No." | "Party IBAN"
	/**	Variable : Data	*/
	variable?: string
}