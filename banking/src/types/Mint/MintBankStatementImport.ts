import { MintBankStatementImportTransactions } from './MintBankStatementImportTransactions'

export interface MintBankStatementImport{
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
	/**	Bank Account : Link - Bank Account	*/
	bank_account: string
	/**	Status : Select	*/
	status: "Not Started" | "Completed" | "Error"
	/**	File : Attach	*/
	file?: string
	/**	File Type : Select	*/
	file_type?: "PDF"
	/**	Transactions : Table - Mint Bank Statement Import Transactions	*/
	transactions?: MintBankStatementImportTransactions[]
	/**	Error : Code	*/
	error?: string
	/**	Amended From : Link - Mint Bank Statement Import	*/
	amended_from?: string
}