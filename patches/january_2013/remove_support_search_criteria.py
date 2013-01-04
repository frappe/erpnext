import webnotes
def execute():
	for sc in ["warranty-amc_expiry_details", "warranty-amc_summary"]:
		webnotes.delete_doc("Search Criteria", sc)