import { PaymentEntryReference } from './PaymentEntryReference'
import { AdvanceTaxesandCharges } from './AdvanceTaxesandCharges'
import { PaymentEntryDeduction } from './PaymentEntryDeduction'

export interface PaymentEntry{
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
	/**	Series : Select	*/
	naming_series: "ACC-PAY-.YYYY.-"
	/**	Payment Type : Select	*/
	payment_type: "Receive" | "Pay" | "Internal Transfer"
	/**	Payment Order Status : Select	*/
	payment_order_status?: "Initiated" | "Payment Ordered"
	/**	Posting Date : Date	*/
	posting_date: string
	/**	Company : Link - Company	*/
	company: string
	/**	Mode of Payment : Link - Mode of Payment	*/
	mode_of_payment?: string
	/**	Party Type : Link - DocType	*/
	party_type?: string
	/**	Party : Dynamic Link	*/
	party?: string
	/**	Party Name : Data	*/
	party_name?: string
	/**	Book Advance Payments in Separate Party Account : Check	*/
	book_advance_payments_in_separate_party_account?: 0 | 1
	/**	Reconcile on Advance Payment Date : Check	*/
	reconcile_on_advance_payment_date?: 0 | 1
	/**	Company Bank Account : Link - Bank Account	*/
	bank_account?: string
	/**	Party Bank Account : Link - Bank Account	*/
	party_bank_account?: string
	/**	Contact : Link - Contact	*/
	contact_person?: string
	/**	Email : Data	*/
	contact_email?: string
	/**	Party Balance : Currency	*/
	party_balance?: number
	/**	Account Paid From : Link - Account	*/
	paid_from: string
	/**	Paid From Account Type : Data	*/
	paid_from_account_type?: string
	/**	Account Currency (From) : Link - Currency	*/
	paid_from_account_currency: string
	/**	Account Balance (From) : Currency	*/
	paid_from_account_balance?: number
	/**	Account Paid To : Link - Account	*/
	paid_to: string
	/**	Paid To Account Type : Data	*/
	paid_to_account_type?: string
	/**	Account Currency (To) : Link - Currency	*/
	paid_to_account_currency: string
	/**	Account Balance (To) : Currency	*/
	paid_to_account_balance?: number
	/**	Paid Amount : Currency	*/
	paid_amount: number
	/**	Paid Amount After Tax : Currency	*/
	paid_amount_after_tax?: number
	/**	Source Exchange Rate : Float	*/
	source_exchange_rate: number
	/**	Paid Amount (Company Currency) : Currency	*/
	base_paid_amount: number
	/**	Paid Amount After Tax (Company Currency) : Currency	*/
	base_paid_amount_after_tax?: number
	/**	Received Amount : Currency	*/
	received_amount: number
	/**	Received Amount After Tax : Currency	*/
	received_amount_after_tax?: number
	/**	Target Exchange Rate : Float	*/
	target_exchange_rate: number
	/**	Received Amount (Company Currency) : Currency	*/
	base_received_amount: number
	/**	Received Amount After Tax (Company Currency) : Currency	*/
	base_received_amount_after_tax?: number
	/**	Payment References : Table - Payment Entry Reference	*/
	references?: PaymentEntryReference[]
	/**	Total Allocated Amount : Currency	*/
	total_allocated_amount?: number
	/**	Total Allocated Amount (Company Currency) : Currency	*/
	base_total_allocated_amount?: number
	/**	Unallocated Amount : Currency	*/
	unallocated_amount?: number
	/**	Difference Amount (Company Currency) : Currency	*/
	difference_amount?: number
	/**	Purchase Taxes and Charges Template : Link - Purchase Taxes and Charges Template	*/
	purchase_taxes_and_charges_template?: string
	/**	Sales Taxes and Charges Template : Link - Sales Taxes and Charges Template	*/
	sales_taxes_and_charges_template?: string
	/**	Apply Tax Withholding Amount : Check	*/
	apply_tax_withholding_amount?: 0 | 1
	/**	Tax Withholding Category : Link - Tax Withholding Category	*/
	tax_withholding_category?: string
	/**	Advance Taxes and Charges : Table - Advance Taxes and Charges	*/
	taxes?: AdvanceTaxesandCharges[]
	/**	Total Taxes and Charges (Company Currency) : Currency	*/
	base_total_taxes_and_charges?: number
	/**	Total Taxes and Charges : Currency	*/
	total_taxes_and_charges?: number
	/**	Payment Deductions or Loss : Table - Payment Entry Deduction	*/
	deductions?: PaymentEntryDeduction[]
	/**	Cheque/Reference No : Data	*/
	reference_no?: string
	/**	Cheque/Reference Date : Date	*/
	reference_date?: string
	/**	Clearance Date : Date	*/
	clearance_date?: string
	/**	Project : Link - Project	*/
	project?: string
	/**	Cost Center : Link - Cost Center	*/
	cost_center?: string
	/**	Status : Select	*/
	status?: "" | "Draft" | "Submitted" | "Cancelled"
	/**	Custom Remarks : Check	*/
	custom_remarks?: 0 | 1
	/**	Remarks : Small Text	*/
	remarks?: string
	/**	In Words (Company Currency) : Small Text	*/
	base_in_words?: string
	/**	Is Opening : Select	*/
	is_opening?: "No" | "Yes"
	/**	Letter Head : Link - Letter Head	*/
	letter_head?: string
	/**	Print Heading : Link - Print Heading	*/
	print_heading?: string
	/**	Bank : Read Only	*/
	bank?: string
	/**	Bank Account No : Read Only	*/
	bank_account_no?: string
	/**	Payment Order : Link - Payment Order	*/
	payment_order?: string
	/**	In Words : Small Text	*/
	in_words?: string
	/**	Auto Repeat : Link - Auto Repeat	*/
	auto_repeat?: string
	/**	Amended From : Link - Payment Entry	*/
	amended_from?: string
	/**	Title : Data	*/
	title?: string
}