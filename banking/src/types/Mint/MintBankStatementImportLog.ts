
export interface MintBankStatementImportLog{
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
	/**	Number of Transactions : Int	*/
	number_of_transactions?: number
	/**	Start Date : Date	*/
	start_date?: string
	/**	End Date : Date	*/
	end_date?: string
	/**	Closing Balance : Currency	*/
	closing_balance?: number
}