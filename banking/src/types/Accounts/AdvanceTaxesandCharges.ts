
export interface AdvanceTaxesandCharges{
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
	/**	Add Or Deduct : Select	*/
	add_deduct_tax: "Add" | "Deduct"
	/**	Type : Select	*/
	charge_type: "" | "Actual" | "On Paid Amount" | "On Previous Row Amount" | "On Previous Row Total"
	/**	Reference Row # : Data	*/
	row_id?: string
	/**	Account Head : Link - Account	*/
	account_head: string
	/**	Description : Small Text	*/
	description: string
	/**	Considered In Paid Amount : Check	*/
	included_in_paid_amount?: 0 | 1
	/**	Cost Center : Link - Cost Center	*/
	cost_center?: string
	/**	Tax Rate : Float	*/
	rate?: number
	/**	Account Currency : Link - Currency	*/
	currency?: string
	/**	Amount : Currency	*/
	tax_amount?: number
	/**	Total : Currency	*/
	total?: number
	/**	Allocated Amount : Currency	*/
	allocated_amount?: number
	/**	Amount (Company Currency) : Currency	*/
	base_tax_amount?: number
	/**	Total (Company Currency) : Currency	*/
	base_total?: number
}