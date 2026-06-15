
export interface BankTransactionPayments {
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
	/**	Payment Document : Link - DocType	*/
	payment_document: string
	/**	Payment Entry : Dynamic Link	*/
	payment_entry: string
	/**	Allocated Amount : Currency	*/
	allocated_amount: number
	/**	Clearance Date : Date	*/
	clearance_date?: string
	/**	Reconciliation Type : Select	*/
	reconciliation_type?: 'Matched' | 'Voucher Created'
}