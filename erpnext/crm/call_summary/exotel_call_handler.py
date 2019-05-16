import frappe

@frappe.whitelist(allow_guest=True)
def handle_request(*args, **kwargs):
	r = frappe.request

	payload = r.get_data()

	print(r.args.to_dict())
	print(payload)

	frappe.publish_realtime('incoming_call', r.args.to_dict())