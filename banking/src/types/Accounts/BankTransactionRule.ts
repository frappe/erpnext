import { BankTransactionRuleDescriptionConditions } from './BankTransactionRuleDescriptionConditions'
import { BankTransactionRuleAccounts } from './BankTransactionRuleAccounts'

export interface BankTransactionRule{
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
	/**	Rule Name : Data	*/
	rule_name: string
	/**	Transaction Type : Select	*/
	transaction_type: "Any" | "Withdrawal" | "Deposit"
	/**	Priority : Int	*/
	priority: number
	/**	Min Amount : Currency	*/
	min_amount?: number
	/**	Max Amount : Currency	*/
	max_amount?: number
	/**	Rule Description : Small Text	*/
	rule_description?: string
	/**	Company : Link - Company	*/
	company: string
	/**	Description Rules : Table - Bank Transaction Rule Description Conditions	*/
	description_rules: BankTransactionRuleDescriptionConditions[]
	/**	Classify As : Select	*/
	classify_as: "Bank Entry" | "Payment Entry" | "Transfer"
	/**	Account : Link - Account	*/
	account?: string
	/**	Bank Entry Type : Select	*/
	bank_entry_type?: "Single Account" | "Multiple Accounts"
	/**	Party Type : Link - DocType	*/
	party_type?: string
	/**	Party : Dynamic Link	*/
	party?: string
	/**	Accounts : Table - Bank Transaction Rule Accounts	*/
	accounts?: BankTransactionRuleAccounts[]
}