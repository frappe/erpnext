// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Opening Invoice Creation Tool', {
	setup: function(frm) {
		frm.set_query('party_type', 'invoices', function(doc, cdt, cdn) {
			return {
				filters: {
					'name': ['in', 'Customer,Supplier']
				}
			};
		});
	},

	refresh: function(frm) {
		frm.disable_save();
		frm.trigger("make_dashboard");
		frm.page.set_primary_action(__("Make Invoices"), () => {
			let btn_primary = frm.page.btn_primary.get(0);
			return frm.call({
				doc: frm.doc,
				freeze: true,
				btn: $(btn_primary),
				method: "make_invoices",
				freeze_message: __("Creating {0} Invoice", [frm.doc.invoice_type]),
				callback: (r) => {
					if(!r.exc){
						frappe.msgprint(__("Opening {0} Invoice created", [frm.doc.invoice_type]));
						frm.clear_table("invoices");
						frm.refresh_fields();
						frm.reload_doc();
					}
				}
			});
		});
	},

	company: function(frm) {
		frappe.call({
			method: 'erpnext.accounting.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool.get_temporary_opening_account',
			args: {
				company: frm.doc.company
			},
			callback: (r) => {
				if (r.message) {
					frm.doc.__onload.temporary_opening_account = r.message;
					frm.trigger('update_invoice_table');
				}
			}
		})
	},

	invoice_type: function(frm) {
		$.each(frm.doc.invoices, (idx, row) => {
			row.party_type = frm.doc.invoice_type == "Sales"? "Customer": "Supplier";
			row.party = "";
		});
		frm.refresh_fields();
	},

	make_dashboard: function(frm) {
		let max_count = frm.doc.__onload.max_count;
		let opening_invoices_summary = frm.doc.__onload.opening_invoices_summary;
		if(!$.isEmptyObject(opening_invoices_summary)) {
			let section = frm.dashboard.add_section(
				frappe.render_template('opening_invoice_creation_tool_dashboard', {
					data: opening_invoices_summary,
					max_count: max_count
				})
			);

			section.on('click', '.invoice-link', function() {
				let doctype = $(this).attr('data-type');
				let company = $(this).attr('data-company');
				frappe.set_route('List', doctype,
					{'is_opening': 'Yes', 'company': company, 'docstatus': 1});
			});
			frm.dashboard.show();
		}
	},

	update_invoice_table: function(frm) {
		$.each(frm.doc.invoices, (idx, row) => {
			if (!row.temporary_opening_account) {
				row.temporary_opening_account = frm.doc.__onload.temporary_opening_account;
			}
			row.party_type = frm.doc.invoice_type == "Sales"? "Customer": "Supplier";
		});
	}
});

frappe.ui.form.on('Opening Invoice Creation Tool Item', {
	invoices_add: (frm) => {
		frm.trigger('update_invoice_table');
	}
});