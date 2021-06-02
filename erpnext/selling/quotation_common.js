frappe.ui.form.on(cur_frm.doctype, {
	transaction_date: function (frm) {
		frm.events.set_valid_till(frm);
	},

	quotation_validity_days: function (frm) {
		frm.events.set_valid_till(frm);
	},

	valid_till: function (frm) {
		frm.events.set_quotation_validity_days(frm);
	},

	set_valid_till: function(frm) {
		if (frm.doc.transaction_date) {
			if (cint(frm.doc.quotation_validity_days) > 0) {
				frm.doc.valid_till = frappe.datetime.add_days(frm.doc.transaction_date, cint(frm.doc.quotation_validity_days)-1);
				frm.refresh_field('valid_till');
			} else if (frm.doc.valid_till && cint(frm.doc.quotation_validity_days) == 0) {
				frm.events.set_quotation_validity_days(frm);
			}
		}
	},

	set_quotation_validity_days: function (frm) {
		if (frm.doc.transaction_date && frm.doc.valid_till) {
			var days = frappe.datetime.get_diff(frm.doc.valid_till, frm.doc.transaction_date) + 1;
			if (days > 0) {
				frm.doc.quotation_validity_days = days;
				frm.refresh_field('quotation_validity_days');
			}
		}
	},

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