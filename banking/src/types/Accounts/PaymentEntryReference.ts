
export interface PaymentEntryReference{
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
	/**	Type : Link - DocType	*/
	reference_doctype: string
	/**	Name : Dynamic Link	*/
	reference_name: string
	/**	Due Date : Date	*/
	due_date?: string
	/**	Supplier Invoice No : Data	*/
	bill_no?: string
	/**	Payment Term : Link - Payment Term	*/
	payment_term?: string
	/**	Payment Term Outstanding : Float	*/
	payment_term_outstanding?: number
	/**	Account Type : Data	*/
	account_type?: string
	/**	Payment Type : Data	*/
	payment_type?: string
	/**	Reconcile Effect On : Date	*/
	reconcile_effect_on?: string
	/**	Grand Total : Float	*/
	total_amount?: number
	/**	Outstanding : Float	*/
	outstanding_amount?: number
	/**	Allocated : Float	*/
	allocated_amount?: number
	/**	Exchange Rate : Float	*/
	exchange_rate?: number
	/**	Exchange Gain/Loss : Currency	*/
	exchange_gain_loss?: number
	/**	Account : Link - Account	*/
	account?: string
	/**	Payment Request : Link - Payment Request	*/
	payment_request?: string
	/**	Payment Request Outstanding : Float	*/
	payment_request_outstanding?: number
}