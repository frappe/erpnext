def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc("accounts", "search_criteria", "debtors_ledger")
	reload_doc("accounts", "search_criteria", "creditors_ledger")