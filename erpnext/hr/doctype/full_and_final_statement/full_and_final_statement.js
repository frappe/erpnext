// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Full And Final Statement', {
	onload: function(frm) {
		frm.events.set_queries(frm, "payables");
		frm.events.set_queries(frm, "receivables");
	},

	set_queries: function(frm, type) {
		frm.set_query('reference_document_type', type, function () {
			let modules = ["HR", "Payroll", "Loan Management"];
			return {
				filters: {
					istable: 0,
					issingle: 0,
					module: ["In", modules]
				}
			};
		});
	},

	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status == "Unpaid") {
			frm.add_custom_button(__('Create Journal Entry'), function () {
				frm.events.create_journal_entry(frm);
			});
		}
	},

	employee: function(frm) {
		frm.events.get_outstanding_statements(frm);
	},

	get_outstanding_statements: function(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: 'get_outstanding_statements',
				doc: frm.doc,
				callback: function() {
					frm.refresh();
				}
			});
		}
	},

	create_journal_entry: function(frm) {
		frappe.call({
			method: "create_journal_entry",
			doc: frm.doc,
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}
});

frappe.ui.form.on('Full And Final Outstanding Statements', {
	reference_document: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.reference_document_type && child.reference_document) {
			frappe.call({
				method: 'erpnext.hr.doctype.full_and_final_statement.full_and_final_statement.get_account_and_amount',
				args: {
					ref_doctype: child.reference_document_type,
					ref_document: child.reference_document
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "account", r.message[0]);
						frappe.model.set_value(cdt, cdn, "amount", r.message[1]);
					}
				}
			});
		}
	},

	amount: function(frm) {
		frm.doc.total_payable_amount = 0;
		frm.doc.total_receivable_amount = 0;

		frm.doc.payables.forEach(element => {
			frm.doc.total_payable_amount += element.amount;
		});

		frm.doc.receivables.forEach(element => {
			frm.doc.total_receivable_amount += element.amount;
		});
		cur_frm.refresh_field("total_payable_amount");
		cur_frm.refresh_field("total_receivable_amount");
	}
});
