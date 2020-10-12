// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transaction Type', {
	setup: function(frm) {
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'account_type': ['in', ['Receivable', 'Payable']],
				'company': d.company,
				"is_group": 0
			};
			return {
				filters: filters
			}
		});
		frm.set_query('cost_center', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'company': d.company,
				"is_group": 0
			};
			return {
				filters: filters
			}
		});
		frm.set_query('document_types_not_allowed', function(doc, cdt, cdn) {
			var already_selected = doc.document_types_not_allowed.map(d => d.document_type);

			var document_types = [];
			if (doc.selling) {
				document_types.push('Quotation');
				document_types.push('Sales Order');
				document_types.push('Delivery Note');
				document_types.push('Sales Invoice');
			}
			if (doc.buying) {
				document_types.push('Supplier Quotation');
				document_types.push('Purchase Order');
				document_types.push('Purchase Receipt');
				document_types.push('Purchase Invoice');
			}
			return {
				filters: [
					['name', 'in', document_types],
					['name', 'not in', already_selected]
				]
			}
		});
	}
});
