frappe.ui.form.on(cur_frm.doctype, {
	set_as_lost_dialog: function(frm) {
		var dialog = new frappe.ui.Dialog({
			title: __("Set as Lost"),
			fields: [
				{
					"fieldtype": "Table MultiSelect",
					"label": __("Lost Reasons"),
					"fieldname": "lost_reason",
					"options": frm.doctype === 'Opportunity' ? 'Opportunity Lost Reason Detail': 'Quotation Lost Reason Detail',
					"reqd": 1
				},
				{
					"fieldtype": "Text",
					"label": __("Detailed Reason"),
					"fieldname": "detailed_reason"
				},
			],
			primary_action: function() {
				var values = dialog.get_values();
				var reasons = values["lost_reason"];
				var detailed_reason = values["detailed_reason"];

				frm.call({
					doc: frm.doc,
					method: 'declare_enquiry_lost',
					args: {
						'lost_reasons_list': reasons,
						'detailed_reason': detailed_reason
					},
					callback: function(r) {
						dialog.hide();
						frm.reload_doc();
					},
				});
				refresh_field("lost_reason");
			},
			primary_action_label: __('Declare Lost')
		});

		dialog.show();
	}
})