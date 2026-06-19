
export interface PaymentEntryDeduction{
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
	/**	Cost Center : Link - Cost Center	*/
	cost_center: string
	/**	Amount (Company Currency) : Currency	*/
	amount: number
	/**	Is Exchange Gain / Loss? : Check	*/
	is_exchange_gain_loss?: 0 | 1
	/**	Description : Small Text	*/
	description?: string
}