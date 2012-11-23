import webnotes

def execute():
	webnotes.delete_doc("Search Criteria", "delivery_note_itemwise_pending_to_bill")

	from webnotes.modules import reload_doc
	reload_doc("accounts", "report", "delivered_items_to_be_billed")