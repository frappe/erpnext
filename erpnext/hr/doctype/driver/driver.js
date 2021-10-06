// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Driver", {
	setup: function(frm) {
		frm.set_query("transporter", function() {
			return {
				filters: {
					is_transporter: 1
				}
			};
		});
	},

	refresh: function(frm) {
		frm.set_query("address", function() {
			return {
				filters: {
					is_your_company_address: !frm.doc.transporter ? 1 : 0
				}
			};
		});
	},
	issuing_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.issuing_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("issuing_date_nepal", resp.message)
				}
			}
		})
	},

	expiry_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.expiry_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("expiry_date_nepal", resp.message)
				}
			}
		})
	},

	transporter: function(frm, cdt, cdn) {
		// this assumes that supplier's address has same title as supplier's name
		frappe.db
			.get_doc("Address", null, { address_title: frm.doc.transporter })
			.then(r => {
				frappe.model.set_value(cdt, cdn, "address", r.name);
			})
			.catch(err => {
				console.log(err);
			});
	}
});
