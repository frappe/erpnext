// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Opening Invoice Creation Tool', {
	setup: (frm) => {
		frm.set_query('party_type', 'invoices', function(doc, cdt, cdn) {
			return {
				filters: {
					'name': ['in', 'Customer,Supplier']
				}
			}
		});
	},

	refresh: (frm) => {
		frm.disable_save();
		this.trigger("make_dashboard");
		frm.page.set_primary_action(__("Make Invoice"), () => {
			btn_primary = frm.page.btn_primary.get(0);
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

	invoice_type: (frm) => {
		$.each(frm.doc.invoices, (idx, row) => {
			row.party_type = frm.doc.invoice_type == "Sales"? "Customer": "Supplier";
			row.party = "";
		});
		frm.refresh_fields();
	},

	make_dashboard: () => {
		let me = this;
		let max_count = this.frm.doc.__onload.max_count;
		let opening_invoices_summery = this.frm.doc.__onload.opening_invoices_summery;
		if(opening_invoices_summery) {
			let section = this.frm.dashboard.add_section(
				frappe.render_template('opening_invoice_creation_tool_dashboard', {
					data: opening_invoices_summery,
					max_count: max_count
				})
			);

			section.on('click', '.invoice-link', function() {
				let doctype = $(this).attr('data-type');
				let company = $(this).attr('data-company');
				frappe.set_route('List', doctype,
					{'is_opening': 'Yes', 'company': me.frm.doc.company, 'docstatus': 1});
			});
		}
		this.frm.dashboard.show();
	}
});

frappe.ui.form.on('Opening Invoice Creation Tool Item', {
	invoices_add: (frm) => {
		$.each(frm.doc.invoices, (idx, row) => {
			row.party_type = frm.doc.invoice_type == "Sales"? "Customer": "Supplier";
		});
	}
})