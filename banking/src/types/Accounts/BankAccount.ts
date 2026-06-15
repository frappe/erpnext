
export interface BankAccount{
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
	/**	Account Name : Data	*/
	account_name: string
	/**	Company Account : Link - Account	*/
	account?: string
	/**	Bank : Link - Bank	*/
	bank: string
	/**	Account Type : Link - Bank Account Type	*/
	account_type?: string
	/**	Account Subtype : Link - Bank Account Subtype	*/
	account_subtype?: string
	/**	Disabled : Check	*/
	disabled?: 0 | 1
	/**	Is Default Account : Check	*/
	is_default?: 0 | 1
	/**	Is Company Account : Check - Setting the account as a Company Account is necessary for Bank Reconciliation	*/
	is_company_account?: 0 | 1
	/**	Company : Link - Company	*/
	company?: string
	/**	Party Type : Link - DocType	*/
	party_type?: string
	/**	Party : Dynamic Link	*/
	party?: string
	/**	IBAN : Data	*/
	iban?: string
	/**	Branch Code : Data	*/
	branch_code?: string
	/**	Bank Account No : Data	*/
	bank_account_no?: string
	/**	Is Credit Card : Check	*/
	is_credit_card?: 0 | 1
	/**	Integration ID : Data	*/
	integration_id?: string
	/**	Last Integration Date : Date - Change this date manually to setup the next synchronization start date	*/
	last_integration_date?: string
	/**	Mask : Data	*/
	mask?: string
}