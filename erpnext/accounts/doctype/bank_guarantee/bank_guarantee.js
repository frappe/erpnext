// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("bank_account", "account", "account");
cur_frm.add_fetch("bank_account", "bank_account_no", "bank_account_no");
cur_frm.add_fetch("bank_account", "iban", "iban");
cur_frm.add_fetch("bank_account", "branch_code", "branch_code");
cur_frm.add_fetch("bank", "swift_number", "swift_number");

frappe.ui.form.on("Bank Guarantee", {
	setup: function (frm) {
		frm.set_query("bank_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					bank: frm.doc.bank,
				},
			};
		});
		frm.set_query("project", function () {
			return {
				filters: {
					customer: frm.doc.customer,
				},
			};
		});
	},

	bg_type: function (frm) {
		if (frm.doc.bg_type == "Receiving") {
			frm.set_value("reference_doctype", "Sales Order");
		} else if (frm.doc.bg_type == "Providing") {
			frm.set_value("reference_doctype", "Purchase Order");
		}
	},

	reference_docname: function (frm) {
		if (frm.doc.reference_docname && frm.doc.reference_doctype) {
			let party_field = frm.doc.reference_doctype == "Sales Order" ? "customer" : "supplier";

			frappe.call({
				method: "erpnext.accounts.doctype.bank_guarantee.bank_guarantee.get_voucher_details",
				args: {
					bank_guarantee_type: frm.doc.bg_type,
					reference_name: frm.doc.reference_docname,
				},
				callback: function (r) {
					if (r.message) {
						if (r.message[party_field]) frm.set_value(party_field, r.message[party_field]);
						if (r.message.project) frm.set_value("project", r.message.project);
						if (r.message.grand_total) frm.set_value("amount", r.message.grand_total);
					}
				},
			});
		}
	},

	start_date: function (frm) {
		var end_date = frappe.datetime.add_days(cur_frm.doc.start_date, cur_frm.doc.validity - 1);
		cur_frm.set_value("end_date", end_date);
	},
	validity: function (frm) {
		var end_date = frappe.datetime.add_days(cur_frm.doc.start_date, cur_frm.doc.validity - 1);
		cur_frm.set_value("end_date", end_date);
	},
});
