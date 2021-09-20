// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Level Agreement', {
	refresh: function(frm) {
		let allow_statuses = [];
		const exclude_statuses = ['Open', 'Closed', 'Resolved'];

		frappe.model.with_doctype('Issue', () => {
			let statuses = frappe.meta.get_docfield('Issue', 'status', frm.doc.name).options;
			statuses = statuses.split('\n');
			allow_statuses = statuses.filter((status) => !exclude_statuses.includes(status));
			frm.fields_dict.pause_sla_on.grid.update_docfield_property(
				'status', 'options', [''].concat(allow_statuses)
			);
		});
	},

	start_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.start_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("start_date_nepali", resp.message)
				}
			}
		})
		set_start_date(this.frm);
	},
	end_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.end_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("end_date_nepali", resp.message)
				}
			}
		})
		set_end_date(this.frm);
	}


});
