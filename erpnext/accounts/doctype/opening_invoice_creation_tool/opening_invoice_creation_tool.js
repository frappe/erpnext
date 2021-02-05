// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Opening Invoice Creation Tool', {
	setup: function(frm) {
		frm.set_query('party_type', 'invoices', function(doc, cdt, cdn) {
			return {
				filters: {
					'name': ['in', 'Customer, Supplier']
				}
			};
		});

		if (frm.doc.company) {
			frm.trigger('setup_company_filters');
		}

		frappe.realtime.on('opening_invoice_creation_progress', data => {
			if (!frm.doc.import_in_progress) {
				frm.dashboard.reset();
				frm.doc.import_in_progress = true;
			}
			if (data.user != frappe.session.user) return;
			if (data.count == data.total) {
				setTimeout((title) => {
					frm.doc.import_in_progress = false;
					frm.clear_table("invoices");
					frm.refresh_fields();
					frm.page.clear_indicator();
					frm.dashboard.hide_progress(title);
					frappe.msgprint(__("Opening {0} Invoice created", [frm.doc.invoice_type]));
				}, 1500, data.title);
				return;
			}

			frm.dashboard.show_progress(data.title, (data.count / data.total) * 100, data.message);
			frm.page.set_indicator(__('In Progress'), 'orange');
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh: function(frm) {
		frm.disable_save();
		!frm.doc.import_in_progress && frm.trigger("make_dashboard");
		frm.page.set_primary_action(__('Create Invoices'), () => {
			let btn_primary = frm.page.btn_primary.get(0);
			return frm.call({
				doc: frm.doc,
				btn: $(btn_primary),
				method: "make_invoices",
				freeze_message: __("Creating {0} Invoice", [frm.doc.invoice_type])
			});
		});

		if (frm.doc.create_missing_party) {
			frm.set_df_property("party", "fieldtype", "Data", frm.doc.name, "invoices");
		}
	},

	setup_company_filters: function(frm) {
		frm.set_query('cost_center', 'invoices', function(doc, cdt, cdn) {
			return {
				filters: {
					'company': doc.company
				}
			};
		});

		frm.set_query('cost_center', function(doc) {
			return {
				filters: {
					'company': doc.company
				}
			};
		});

		frm.set_query('temporary_opening_account', 'invoices', function(doc, cdt, cdn) {
			return {
				filters: {
					'company': doc.company
				}
			}
		});
	},

	company: function(frm) {
		if (frm.doc.company) {

			frm.trigger('setup_company_filters');

			frappe.call({
				method: 'erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool.get_temporary_opening_account',
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
		}
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
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
				}),
				__("Opening Invoices Summary")
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

			if(!row.cost_center) {
				row.cost_center = frm.doc.cost_center;
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