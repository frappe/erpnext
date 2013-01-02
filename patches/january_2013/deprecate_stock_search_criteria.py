import webnotes

def execute():
	for sc in ["itemwise_price_list", "itemwise_receipt_details",
			"shortage_to_purchase_request", "stock_aging_report",
			"stock_ledger", "stock_level", "stock_report",
			"custom_test2", "custom_test3", "custom_test4",
			"test_so2", "test_so3"]:
		webnotes.delete_doc("Search Criteria", sc)