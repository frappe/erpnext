
export interface MintSettings{
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
	/**	Match Transfers across (days) : Int - Number of days to consider for transfer matching across bank accounts.	*/
	transfer_match_days?: number
	/**	Automatically run rules on unreconciled transactions : Check - If checked, this job will run every 30 minutes	*/
	automatically_run_rules_on_unreconciled_transactions?: 0 | 1
	/**	Google Project ID : Data	*/
	google_project_id?: string
	/**	Google Processor Location : Select	*/
	google_processor_location?: "us" | "eu"
	/**	Google Service Account JSON Key : Password	*/
	google_service_account_json_key?: string
	/**	Google Document Processor - Bank Statement : Data	*/
	bank_statement_gdoc_processor?: string
}