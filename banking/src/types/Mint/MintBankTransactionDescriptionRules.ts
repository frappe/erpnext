
export interface MintBankTransactionDescriptionRules{
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
	/**	Check : Select	*/
	check: "Contains" | "Starts With" | "Ends With" | "Regex"
	/**	Value : Small Text	*/
	value: string
}