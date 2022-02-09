// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}
frappe.provide("erpnext.crm");

cur_frm.email_field = "contact_email";
frappe.ui.form.on("Opportunity", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Quotation': 'Quotation',
			'Supplier Quotation': 'Supplier Quotation'
		};

		frm.set_query("opportunity_from", function() {
			return{
				"filters": {
					"name": ["in", ["Customer", "Lead", "Prospect"]],
				}
			}
		});

		if (frm.doc.opportunity_from && frm.doc.party_name){
			frm.trigger('set_contact_link');
		}
	},

	validate: function(frm) {
		if (frm.doc.status == "Lost" && !frm.doc.lost_reasons.length) {
			frm.trigger('set_as_lost_dialog');
			frappe.throw(__("Lost Reasons are required in case opportunity is Lost."));
		}
	},

	contact_date: function(frm) {
		if(frm.doc.contact_date < frappe.datetime.now_datetime()){
			frm.set_value("contact_date", "");
			frappe.throw(__("Next follow up date should be greater than now."))
		}
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	party_name: function(frm) {
		frm.trigger('set_contact_link');

		if (frm.doc.opportunity_from == "Customer") {
			erpnext.utils.get_party_details(frm);
		} else if (frm.doc.opportunity_from == "Lead") {
			erpnext.utils.map_current_doc({
				method: "erpnext.crm.doctype.lead.lead.make_opportunity",
				source_name: frm.doc.party_name,
				frm: frm
			});
		}
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	status:function(frm){
		if (frm.doc.status == "Lost"){
			frm.trigger('set_as_lost_dialog');
		}

	},

	customer_address: function(frm, cdt, cdn) {
		erpnext.utils.get_address_display(frm, 'customer_address', 'address_display', false);
	},

	contact_person: erpnext.utils.get_contact_details,

	opportunity_from: function(frm) {
		frm.trigger('setup_opportunity_from');

		frm.set_value("party_name", "");
	},

	setup_opportunity_from: function(frm) {
		frm.trigger('setup_queries');
		frm.trigger("set_dynamic_field_label");
	},

	refresh: function(frm) {
		var doc = frm.doc;
		frm.trigger('setup_opportunity_from');
		erpnext.toggle_naming_series();

		if(!frm.is_new() && doc.status!=="Lost") {
			if(doc.with_items){
				frm.add_custom_button(__('Supplier Quotation'),
					function() {
						frm.trigger("make_supplier_quotation")
					}, __('Create'));

				frm.add_custom_button(__('Request For Quotation'),
					function() {
						frm.trigger("make_request_for_quotation")
					}, __('Create'));
			}

			if (frm.doc.opportunity_from != "Customer") {
				frm.add_custom_button(__('Customer'),
					function() {
						frm.trigger("make_customer")
					}, __('Create'));
			}

			frm.add_custom_button(__('Quotation'),
				function() {
					frm.trigger("create_quotation")
				}, __('Create'));
		}

		if(!frm.doc.__islocal && frm.perm[0].write && frm.doc.docstatus==0) {
			if(frm.doc.status==="Open") {
				frm.add_custom_button(__("Close"), function() {
					frm.set_value("status", "Closed");
					frm.save();
				});
			} else {
				frm.add_custom_button(__("Reopen"), function() {
					frm.set_value("lost_reasons",[])
					frm.set_value("status", "Open");
					frm.save();
				});
			}
		}
	},

	set_contact_link: function(frm) {
		if(frm.doc.opportunity_from == "Customer" && frm.doc.party_name) {
			frappe.dynamic_link = {doc: frm.doc, fieldname: 'party_name', doctype: 'Customer'}
		} else if(frm.doc.opportunity_from == "Lead" && frm.doc.party_name) {
			frappe.dynamic_link = {doc: frm.doc, fieldname: 'party_name', doctype: 'Lead'}
		}
	},

	currency: function(frm) {
		let company_currency = erpnext.get_currency(frm.doc.company);
		if (company_currency != frm.doc.company) {
			frappe.call({
				method: "erpnext.setup.utils.get_exchange_rate",
				args: {
					from_currency: frm.doc.currency,
					to_currency: company_currency
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('conversion_rate', flt(r.message));
						frm.set_df_property('conversion_rate', 'description', '1 ' + frm.doc.currency
						+ ' = [?] ' + company_currency);
					}
				}
			});
		} else {
			frm.set_value('conversion_rate', 1.0);
			frm.set_df_property('conversion_rate', 'hidden', 1);
			frm.set_df_property('conversion_rate', 'description', '');
		}

		frm.trigger('opportunity_amount');
		frm.trigger('set_dynamic_field_label');
	},

	opportunity_amount: function(frm) {
		frm.set_value('base_opportunity_amount', flt(frm.doc.opportunity_amount) * flt(frm.doc.conversion_rate));
	},

	set_dynamic_field_label: function(frm){
		if (frm.doc.opportunity_from) {
			frm.set_df_property("party_name", "label", frm.doc.opportunity_from);
		}
		frm.trigger('change_grid_labels');
		frm.trigger('change_form_labels');
	},

	make_supplier_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_supplier_quotation",
			frm: frm
		})
	},

	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_request_for_quotation",
			frm: frm
		})
	},

	change_form_labels: function(frm) {
		let company_currency = erpnext.get_currency(frm.doc.company);
		frm.set_currency_labels(["base_opportunity_amount", "base_total"], company_currency);
		frm.set_currency_labels(["opportunity_amount", "total"], frm.doc.currency);

		// toggle fields
		frm.toggle_display(["conversion_rate", "base_opportunity_amount", "base_total"],
			frm.doc.currency != company_currency);
	},

	change_grid_labels: function(frm) {
		let company_currency = erpnext.get_currency(frm.doc.company);
		frm.set_currency_labels(["base_rate", "base_amount"], company_currency, "items");
		frm.set_currency_labels(["rate", "amount"], frm.doc.currency, "items");

		let item_grid = frm.fields_dict.items.grid;
		$.each(["base_rate", "base_amount"], function(i, fname) {
			if(frappe.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, frm.doc.currency != company_currency);
		});
		frm.refresh_fields();
	},

	calculate_total: function(frm) {
		let total = 0, base_total = 0;
		frm.doc.items.forEach(item => {
			total += item.amount;
			base_total += item.base_amount;
		})

		frm.set_value({
			'total': flt(total),
			'base_total': flt(base_total)
		});
	}

});
frappe.ui.form.on("Opportunity Item", {
	calculate: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
		frappe.model.set_value(cdt, cdn, "base_rate", flt(frm.doc.conversion_rate) * flt(row.rate));
		frappe.model.set_value(cdt, cdn, "base_amount", flt(frm.doc.conversion_rate) * flt(row.amount));
		frm.trigger("calculate_total");
	},
	qty: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	rate: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	}
})

// TODO commonify this code
erpnext.crm.Opportunity = class Opportunity extends frappe.ui.form.Controller {
	onload() {

		if(!this.frm.doc.status) {
			frm.set_value('status', 'Open');
		}
		if(!this.frm.doc.company && frappe.defaults.get_user_default("Company")) {
			frm.set_value('company', frappe.defaults.get_user_default("Company"));
		}
		if(!this.frm.doc.currency) {
			frm.set_value('currency', frappe.defaults.get_user_default("Currency"));
		}

		this.setup_queries();
		this.frm.trigger('currency');
	}

	setup_queries() {
		var me = this;

		if(this.frm.fields_dict.contact_by.df.options.match(/^User/)) {
			this.frm.set_query("contact_by", erpnext.queries.user);
		}

		me.frm.set_query('customer_address', erpnext.queries.address_query);

		this.frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {'is_sales_item': 1}
			};
		});

		me.frm.set_query('contact_person', erpnext.queries['contact_query'])

		if (me.frm.doc.opportunity_from == "Lead") {
			me.frm.set_query('party_name', erpnext.queries['lead']);
		}
		else if (me.frm.doc.opportunity_from == "Customer") {
			me.frm.set_query('party_name', erpnext.queries['customer']);
		}
	}

	create_quotation() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
			frm: cur_frm
		})
	}

	make_customer() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_customer",
			frm: cur_frm
		})
	}
};

extend_cscript(cur_frm.cscript, new erpnext.crm.Opportunity({frm: cur_frm}));

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return frappe.call({
			method: "erpnext.crm.doctype.opportunity.opportunity.get_item_details",
			args: {"item_code":d.item_code},
			callback: function(r, rt) {
				if(r.message) {
					$.each(r.message, function(k, v) {
						frappe.model.set_value(cdt, cdn, k, v);
					});
					refresh_field('image_view', d.name, 'items');
				}
			}
		})
	}
}
