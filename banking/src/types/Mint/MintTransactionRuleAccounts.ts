
export interface MintTransactionRuleAccounts{
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
	/**	Party Type : Link - Party Type	*/
	party_type?: string
	/**	Party : Dynamic Link	*/
	party?: string
	/**	Debit : Data	*/
	debit?: string
	/**	Credit : Data	*/
	credit?: string
	/**	User Remark : Small Text	*/
	user_remark?: string
}