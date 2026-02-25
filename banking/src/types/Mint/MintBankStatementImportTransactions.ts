
export interface MintBankStatementImportTransactions{
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
	/**	Date : Date	*/
	date: string
	/**	Amount : Currency	*/
	amount?: number
	/**	Type : Select	*/
	type?: "Withdrawal" | "Deposit"
	/**	Imported : Check	*/
	imported?: 0 | 1
	/**	String Amount : Data - Can be "1200 Dr" and will be translated to 1200 in amount and "Withdrawal"	*/
	string_amount?: string
	/**	Description : Small Text	*/
	description?: string
	/**	Reference : Data	*/
	reference?: string
}