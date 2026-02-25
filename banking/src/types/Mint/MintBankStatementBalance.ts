
export interface MintBankStatementBalance{
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
	/**	Date : Date	*/
	date: string
	/**	Balance : Currency	*/
	balance: number
}