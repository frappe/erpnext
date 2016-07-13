frappe.listview_settings['Payment Entry'] = {
	add_fields: ["payment_type"],
	get_indicator: function(doc) {
		return [__(doc.payment_type), (doc.docstatus==0 ? 'red' : 'blue'), 'status=' + doc.payment_type]
	}
}
