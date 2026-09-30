// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Guarantee", {
	setup: function (frm) {
		frm.add_fetch("bank_account", "account", "account");
		frm.add_fetch("bank_account", "bank_account_no", "bank_account_no");
		frm.add_fetch("bank_account", "iban", "iban");
		frm.add_fetch("bank_account", "branch_code", "branch_code");
		frm.add_fetch("bank", "swift_number", "swift_number");

		frm.set_query("reference_doctype", function () {
			return {
				filters: {
					name: ["in", ["Sales Order", "Purchase Order"]],
				},
			};
		});
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
		frm.events.set_end_date(frm);
	},

	validity: function (frm) {
		frm.events.set_end_date(frm);
	},

	set_end_date: function (frm) {
		let end_date = frappe.datetime.add_days(frm.doc.start_date, frm.doc.validity - 1);
		frm.set_value("end_date", end_date);
	},
});
