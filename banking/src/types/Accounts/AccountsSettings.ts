
export interface AccountsSettings {
	name: string
	creation: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx: number
	/**	Enable Audit Trail : Check - In accordance with <a href="https://egazette.gov.in/WriteReadData/2021/226081.pdf" target="_blank" rel="noopener noreferrer"> MCA Notification dated 24-03-2021</a>, enabling this feature will ensure that each change made to the books of account gets recorded. Once enabled, this feature cannot be disabled.	*/
	enable_audit_trail?: 0 | 1
	/**	Unlink Payment on Cancellation of Invoice : Check	*/
	unlink_payment_on_cancellation_of_invoice?: 0 | 1
	/**	Unlink Advance Payment on Cancellation of Order : Check	*/
	unlink_advance_payment_on_cancelation_of_order?: 0 | 1
	/**	Delete Accounting and Stock Ledger Entries on deletion of Transaction : Check	*/
	delete_linked_ledger_entries?: 0 | 1
	/**	Enable Immutable Ledger : Check - On enabling this cancellation entries will be posted on the actual cancellation date and reports will consider cancelled entries as well	*/
	enable_immutable_ledger?: 0 | 1
	/**	Check Supplier Invoice Number Uniqueness : Check - Enabling this ensures each Purchase Invoice has a unique value in Supplier Invoice No. field within a particular fiscal year	*/
	check_supplier_invoice_uniqueness?: 0 | 1
	/**	Automatically Fetch Payment Terms from Order/Quotation : Check - Payment Terms from orders will be fetched into the invoices as is	*/
	automatically_fetch_payment_terms?: 0 | 1
	/**	Enable Subscription : Check - Enable Subscription tracking in invoice	*/
	enable_subscription?: 0 | 1
	/**	Enable Common Party Accounting : Check - Learn about <a href="https://docs.frappe.io/erpnext/user/manual/en/common_party_accounting" rel="noopener noreferrer">Common Party</a>	*/
	enable_common_party_accounting?: 0 | 1
	/**	Allow multi-currency invoices against single party account  : Check - Enabling this will allow creation of multi-currency invoices against single party account in company currency	*/
	allow_multi_currency_invoices_against_single_party_account?: 0 | 1
	/**	Confirm before resetting posting date : Check - If enabled, user will be alerted before resetting posting date to current date in relevant transactions	*/
	confirm_before_resetting_posting_date?: 0 | 1
	/**	Enable Accounting Dimensions : Check - Enable cost center, projects and other custom accounting dimensions	*/
	enable_accounting_dimensions?: 0 | 1
	/**	Enable Discounts and Margin : Check - Apply discounts and margins on products	*/
	enable_discounts_and_margin?: 0 | 1
	/**	Merge Similar Account Heads : Check - Rows with Same Account heads will be merged on Ledger	*/
	merge_similar_account_heads?: 0 | 1
	/**	Book Deferred Entries Based On : Select - If "Months" is selected, a fixed amount will be booked as deferred revenue or expense for each month irrespective of the number of days in a month. It will be prorated if deferred revenue or expense is not booked for an entire month	*/
	book_deferred_entries_based_on?: "Days" | "Months"
	/**	Automatically Process Deferred Accounting Entry : Check	*/
	automatically_process_deferred_accounting_entry?: 0 | 1
	/**	Book Deferred Entries Via Journal Entry : Check - If this is unchecked, direct GL entries will be created to book deferred revenue or expense	*/
	book_deferred_entries_via_journal_entry?: 0 | 1
	/**	Submit Journal Entries : Check - If this is unchecked Journal Entries will be saved in a Draft state and will have to be submitted manually	*/
	submit_journal_entries?: 0 | 1
	/**	Determine Address Tax Category From : Select - Address used to determine Tax Category in transactions	*/
	determine_address_tax_category_from?: "Billing Address" | "Shipping Address"
	/**	Automatically Add Taxes and Charges from Item Tax Template : Check - Overridden by India Compliance	*/
	add_taxes_from_item_tax_template?: 0 | 1
	/**	Automatically Add Taxes from Taxes and Charges Template : Check - If no taxes are set, and Taxes and Charges Template is selected, the system will automatically apply the taxes from the chosen template.	*/
	add_taxes_from_taxes_and_charges_template?: 0 | 1
	/**	Book Tax Loss on Early Payment Discount : Check - Split Early Payment Discount Loss into Income and Tax Loss	*/
	book_tax_discount_loss?: 0 | 1
	/**	Round Tax Amount Row-wise : Check - Tax Amount will be rounded on a row(items) level	*/
	round_row_wise_tax?: 0 | 1
	/**	Show Inclusive Tax in Print : Check	*/
	show_inclusive_tax_in_print?: 0 | 1
	/**	Show Taxes as Table in Print : Check	*/
	show_taxes_as_table_in_print?: 0 | 1
	/**	Show Payment Schedule in Print : Check	*/
	show_payment_schedule_in_print?: 0 | 1
	/**	Maintain Same Rate Throughout Internal Transaction : Check	*/
	maintain_same_internal_transaction_rate?: 0 | 1
	/**	Fetch Valuation Rate for Internal Transaction : Check	*/
	fetch_valuation_rate_for_internal_transaction?: 0 | 1
	/**	Action if Same Rate is Not Maintained Throughout  Internal Transaction : Select	*/
	maintain_same_rate_action?: "Stop" | "Warn"
	/**	Role Allowed to Override Stop Action : Link - Role	*/
	role_to_override_stop_action?: string
	/**	Allow Stale Exchange Rates : Check	*/
	allow_stale?: 0 | 1
	/**	Allow Implicit Pegged Currency Conversion : Check - System will do an implicit conversion using the pegged currency. <br>
Ex: Instead of AED -&gt; INR, system will do AED -&gt; USD -&gt; INR using the pegged exchange rate of AED against USD.	*/
	allow_pegged_currencies_exchange_rates?: 0 | 1
	/**	Stale Days : Int	*/
	stale_days?: number
	/**	Auto Reconcile Payments : Check	*/
	auto_reconcile_payments?: 0 | 1
	/**	Auto Reconciliation Job Trigger : Int - Interval should be between 1 to 59 MInutes	*/
	auto_reconciliation_job_trigger?: number
	/**	Reconciliation Queue Size : Int - Documents Processed on each trigger. Queue Size should be between 5 and 100	*/
	reconciliation_queue_size?: number
	/**	Posting Date Inheritance for Exchange Gain / Loss : Select - Only applies for Normal Payments	*/
	exchange_gain_loss_posting_date?: "Invoice" | "Payment" | "Reconciliation Date"
	/**	Enable Loyalty Point Program : Check	*/
	enable_loyalty_point_program?: 0 | 1
	/**	Fetch Payment Schedule In Payment Request : Check	*/
	fetch_payment_schedule_in_payment_request?: 0 | 1
	/**	Over Billing Allowance (%) : Currency - The percentage you are allowed to bill more against the amount ordered. For example, if the order value is $100 for an item and tolerance is set as 10%, then you are allowed to bill up to $110 	*/
	over_billing_allowance?: number
	/**	Role Allowed to Over Bill  : Link - Role - Users with this role are allowed to over bill above the allowance percentage	*/
	role_allowed_to_over_bill?: string
	/**	Role allowed to bypass Credit Limit : Link - Role	*/
	credit_controller?: string
	/**	Make Payment via Journal Entry : Check	*/
	make_payment_via_journal_entry?: 0 | 1
	/**	Calculate daily depreciation using total days in depreciation period : Check - Enable this option to calculate daily depreciation by considering the total number of days in the entire depreciation period, (including leap years) while using daily pro-rata based depreciation	*/
	calculate_depr_using_total_days?: 0 | 1
	/**	Book Asset Depreciation Entry Automatically : Check	*/
	book_asset_depreciation_entry_automatically?: 0 | 1
	/**	Role to Notify on Depreciation Failure : Link - Role - Users with this role will be notified if the asset depreciation gets failed	*/
	role_to_notify_on_depreciation_failure?: string
	/**	Ignore Account Closing Balance : Check - Financial reports will be generated using GL Entry doctypes (should be enabled if Period Closing Voucher is not posted for all years sequentially or missing) 	*/
	ignore_account_closing_balance?: 0 | 1
	/**	Use Legacy Controller For Period Closing Voucher : Check	*/
	use_legacy_controller_for_pcv?: 0 | 1
	/**	General Ledger : Int - Truncates 'Remarks' column to set character length	*/
	general_ledger_remarks_length?: number
	/**	Accounts Receivable/Payable : Int - Truncates 'Remarks' column to set character length	*/
	receivable_payable_remarks_length?: number
	/**	Data Fetch Method : Select	*/
	receivable_payable_fetch_method?: "Buffered Cursor" | "UnBuffered Cursor" | "Raw SQL"
	/**	Default Ageing Range : Data	*/
	default_ageing_range?: string
	/**	Ignore Is Opening check for reporting : Check - Ignores legacy Is Opening field in GL Entry that allows adding opening balance post the system is in use while generating reports	*/
	ignore_is_opening_check_for_reporting?: 0 | 1
	/**	Show Balances in Chart Of Accounts : Check	*/
	show_balance_in_coa?: 0 | 1
	/**	Enable Automatic Party Matching : Check - Auto match and set the Party in Bank Transactions	*/
	enable_party_matching?: 0 | 1
	/**	Enable Fuzzy Matching : Check - Approximately match the description/party name against parties	*/
	enable_fuzzy_matching?: 0 | 1
	/**	Match transfers within 'N' days : Int - Number of days to consider for matching transfers across bank accounts	*/
	transfer_match_days?: number
	/**	Automatically run rules on unreconciled transactions : Check - If enabled, rule matching algorithm will run every hour	*/
	automatically_run_rules_on_unreconciled_transactions?: 0 | 1
	/**	Create in Draft Status : Check - Payment Requests made from Sales / Purchase Invoice will be put in Draft explicitly	*/
	create_pr_in_draft_status?: 0 | 1
	/**	Use Legacy Budget Controller : Check	*/
	use_legacy_budget_controller?: 0 | 1
}