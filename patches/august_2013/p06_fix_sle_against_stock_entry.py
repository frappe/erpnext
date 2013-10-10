import webnotes

def execute():
	cancelled = []
	uncancelled = []

	stock_entries = webnotes.conn.sql("""select * from `tabStock Entry` 
		where docstatus >= 1 and date(modified) >= "2013-08-16" 
		and ifnull(production_order, '') != '' and ifnull(bom_no, '') != '' 
		order by modified desc, name desc""", as_dict=True)

	for entry in stock_entries:
		if not webnotes.conn.sql("""select name from `tabStock Entry Detail` 
			where parent=%s""", entry.name):
				res = webnotes.conn.sql("""select * from `tabStock Ledger Entry`
					where voucher_type='Stock Entry' and voucher_no=%s
					and is_cancelled='No'""", entry.name, as_dict=True)
				if res:
					make_stock_entry_detail(entry, res, cancelled, uncancelled)
				
	if cancelled or uncancelled:
		send_email(cancelled, uncancelled)
			
def make_stock_entry_detail(entry, res, cancelled, uncancelled):
	fg_item = webnotes.conn.get_value("Production Order", entry.production_order,
		"production_item")
	voucher_detail_entries_map = {}
	for sle in res:
		voucher_detail_entries_map.setdefault(sle.voucher_detail_no, []).append(sle)
	
	for i, voucher_detail_no in enumerate(sorted(voucher_detail_entries_map.keys())):
		sl_entries = voucher_detail_entries_map[voucher_detail_no]
		# create stock entry details back from stock ledger entries
		stock_entry_detail = webnotes.doc({
			"doctype": "Stock Entry Detail",
			"parentfield": "mtn_details",
			"parenttype": "Stock Entry",
			"parent": entry.name,
			"__islocal": 1,
			"idx": i+1,
			"docstatus": 1,
			"owner": entry.owner,
			"name": voucher_detail_no,
			"transfer_qty": abs(sl_entries[0].actual_qty),
			"qty": abs(sl_entries[0].actual_qty),
			"stock_uom": sl_entries[0].stock_uom,
			"uom": sl_entries[0].stock_uom,
			"conversion_factor": 1,
			"item_code": sl_entries[0].item_code,
			"description": webnotes.conn.get_value("Item", sl_entries[0].item_code,
				"description"),
			"incoming_rate": sl_entries[0].incoming_rate,
			"batch_no": sl_entries[0].batch_no,
			"serial_no": sl_entries[0].serial_no
		})
		
		if sl_entries[0].item_code == fg_item:
			stock_entry_detail.bom_no = entry.bom_no
		
		for sle in sl_entries:
			if sle.actual_qty < 0:
				stock_entry_detail.s_warehouse = sle.warehouse
			else:
				stock_entry_detail.t_warehouse = sle.warehouse
				
		stock_entry_detail.save()
		
	if entry.docstatus == 2:
		webnotes.conn.set_value("Stock Entry", entry.name, "docstatus", 1)
		
		# call for cancelled ones
		se = webnotes.bean("Stock Entry", entry.name)
		controller = se.make_controller()
		controller.update_production_order(1)
		
		res = webnotes.conn.sql("""select name from `tabStock Entry`
			where amended_from=%s""", entry.name)
		if res:
			cancelled.append(res[0][0])
			if res[0][0] in uncancelled:
				uncancelled.remove(res[0][0])
				
			webnotes.bean("Stock Entry", res[0][0]).cancel()

		uncancelled.append(se.doc.name)
		
def send_email(cancelled, uncancelled):
	from webnotes.utils.email_lib import sendmail_to_system_managers
	uncancelled = "we have undone the cancellation of the following Stock Entries through a patch:\n" + \
		"\n".join(uncancelled) if uncancelled else ""
	cancelled = "and cancelled the following Stock Entries:\n" + "\n".join(cancelled) \
		if cancelled else ""

	subject = "[ERPNext] [Important] Cancellation undone for some Stock Entries"
	content = """Dear System Manager, 

An error got introduced into the code that cleared the item table in a Stock Entry associated to a Production Order.

To undo its effect, 
%s

%s

You will have to edit them again.

Sorry for the inconvenience this has caused.

Regards,
Team ERPNext.""" % (uncancelled, cancelled)

	# print subject, content

	sendmail_to_system_managers(subject, content)