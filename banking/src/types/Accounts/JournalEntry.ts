import { JournalEntryAccount } from './JournalEntryAccount'

export interface JournalEntry{
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
	/**	Is System Generated : Check	*/
	is_system_generated?: 0 | 1
	/**	Title : Data	*/
	title?: string
	/**	Entry Type : Select	*/
	voucher_type: "Journal Entry" | "Inter Company Journal Entry" | "Bank Entry" | "Cash Entry" | "Credit Card Entry" | "Debit Note" | "Credit Note" | "Contra Entry" | "Excise Entry" | "Write Off Entry" | "Opening Entry" | "Depreciation Entry" | "Exchange Rate Revaluation" | "Exchange Gain Or Loss" | "Deferred Revenue" | "Deferred Expense"
	/**	Series : Select	*/
	naming_series: "ACC-JV-.YYYY.-"
	/**	Finance Book : Link - Finance Book	*/
	finance_book?: string
	/**	Process Deferred Accounting : Link - Process Deferred Accounting	*/
	process_deferred_accounting?: string
	/**	Reversal Of : Link - Journal Entry	*/
	reversal_of?: string
	/**	Tax Withholding Category : Link - Tax Withholding Category	*/
	tax_withholding_category?: string
	/**	From Template : Link - Journal Entry Template	*/
	from_template?: string
	/**	Company : Link - Company	*/
	company: string
	/**	Posting Date : Date	*/
	posting_date: string
	/**	Apply Tax Withholding Amount  : Check	*/
	apply_tds?: 0 | 1
	/**	Accounting Entries : Table - Journal Entry Account	*/
	accounts: JournalEntryAccount[]
	/**	Reference Number : Data	*/
	cheque_no?: string
	/**	Reference Date : Date	*/
	cheque_date?: string
	/**	User Remark : Small Text	*/
	user_remark?: string
	/**	Total Debit : Currency	*/
	total_debit?: number
	/**	Total Credit : Currency	*/
	total_credit?: number
	/**	Difference (Dr - Cr) : Currency	*/
	difference?: number
	/**	Multi Currency : Check	*/
	multi_currency?: 0 | 1
	/**	Total Amount Currency : Link - Currency	*/
	total_amount_currency?: string
	/**	Total Amount : Currency	*/
	total_amount?: number
	/**	Total Amount in Words : Data	*/
	total_amount_in_words?: string
	/**	Clearance Date : Date	*/
	clearance_date?: string
	/**	Remark : Small Text	*/
	remark?: string
	/**	Paid Loan : Data	*/
	paid_loan?: string
	/**	Inter Company Journal Entry Reference : Link - Journal Entry	*/
	inter_company_journal_entry_reference?: string
	/**	Bill No : Data	*/
	bill_no?: string
	/**	Bill Date : Date	*/
	bill_date?: string
	/**	Due Date : Date	*/
	due_date?: string
	/**	Write Off Based On : Select	*/
	write_off_based_on?: "Accounts Receivable" | "Accounts Payable"
	/**	Write Off Amount : Currency	*/
	write_off_amount?: number
	/**	Pay To / Recd From : Data	*/
	pay_to_recd_from?: string
	/**	Letter Head : Link - Letter Head	*/
	letter_head?: string
	/**	Print Heading : Link - Print Heading	*/
	select_print_heading?: string
	/**	Mode of Payment : Link - Mode of Payment	*/
	mode_of_payment?: string
	/**	Payment Order : Link - Payment Order	*/
	payment_order?: string
	/**	Is Opening : Select	*/
	is_opening?: "No" | "Yes"
	/**	Stock Entry : Link - Stock Entry	*/
	stock_entry?: string
	/**	Auto Repeat : Link - Auto Repeat	*/
	auto_repeat?: string
	/**	Amended From : Link - Journal Entry	*/
	amended_from?: string
}