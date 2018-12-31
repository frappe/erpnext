// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.crm");

cur_frm.email_field = "contact_email";
frappe.ui.form.on("Opportunity", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Quotation': 'Quotation',
			'Supplier Quotation': 'Supplier Quotation'
		}
	},
	customer: function(frm) {
		frm.trigger('set_contact_link');
		erpnext.utils.get_party_details(frm);
	},

	lead: function(frm) {
		frm.trigger('set_contact_link');
	},

	with_items: function(frm) {
		frm.trigger('toggle_mandatory');
	},

	customer_address: function(frm, cdt, cdn) {
		erpnext.utils.get_address_display(frm, 'customer_address', 'address_display', false);
	},

	contact_person: erpnext.utils.get_contact_details,

	enquiry_from: function(frm) {
		frm.toggle_reqd("lead", frm.doc.enquiry_from==="Lead");
		frm.toggle_reqd("customer", frm.doc.enquiry_from==="Customer");
	},

	refresh: function(frm) {
		var doc = frm.doc;
		frm.events.enquiry_from(frm);
		frm.trigger('set_contact_link');
		frm.trigger('toggle_mandatory');
		erpnext.toggle_naming_series();

		if(!doc.__islocal && doc.status!=="Lost") {
			if(doc.with_items){
				frm.add_custom_button(__('Supplier Quotation'),
					function() {
						frm.trigger("make_supplier_quotation")
					}, __('Create'));
			}

			frm.add_custom_button(__('Quotation'),
				cur_frm.cscript.create_quotation, __('Create'));

			if(doc.status!=="Quotation") {
				frm.add_custom_button(__('Lost'),
					cur_frm.cscript['Declare Opportunity Lost']);
			}
		}

		if(!frm.doc.__islocal && frm.perm[0].write && frm.doc.docstatus==0) {
			if(frm.doc.status==="Open") {
				frm.add_custom_button(__("Close"), function() {
					frm.set_value("status", "Closed");
					frm.save();
				});
			} else {
				frm.add_custom_button(__("Reopen"), function() {
					frm.set_value("status", "Open");
					frm.save();
				});
			}
		}
	},

	set_contact_link: function(frm) {
		if(frm.doc.customer) {
			frappe.dynamic_link = {doc: frm.doc, fieldname: 'customer', doctype: 'Customer'}
		} else if(frm.doc.lead) {
			frappe.dynamic_link = {doc: frm.doc, fieldname: 'lead', doctype: 'Lead'}
		}
	},

	make_supplier_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_supplier_quotation",
			frm: cur_frm
		})
	},

	toggle_mandatory: function(frm) {
		frm.toggle_reqd("items", frm.doc.with_items ? 1:0);
	}
})

// TODO commonify this code
erpnext.crm.Opportunity = frappe.ui.form.Controller.extend({
	onload: function() {
		if(!this.frm.doc.enquiry_from && this.frm.doc.customer)
			this.frm.doc.enquiry_from = "Customer";
		if(!this.frm.doc.enquiry_from && this.frm.doc.lead)
			this.frm.doc.enquiry_from = "Lead";

		if(!this.frm.doc.status)
			set_multiple(this.frm.doc.doctype, this.frm.doc.name, { status:'Open' });
		if(!this.frm.doc.company && frappe.defaults.get_user_default("Company"))
			set_multiple(this.frm.doc.doctype, this.frm.doc.name,
				{ company:frappe.defaults.get_user_default("Company") });
		if(!this.frm.doc.currency)
			set_multiple(this.frm.doc.doctype, this.frm.doc.name, { currency:frappe.defaults.get_user_default("Currency") });

		this.setup_queries();
	},

	setup_queries: function() {
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

		$.each([["lead", "lead"],
			["customer", "customer"],
			["contact_person", "contact_query"]],
			function(i, opts) {
				me.frm.set_query(opts[0], erpnext.queries[opts[1]]);
			});
	},

	create_quotation: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
			frm: cur_frm
		})
	}
});

$.extend(cur_frm.cscript, new erpnext.crm.Opportunity({frm: cur_frm}));

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	if(doc.enquiry_from == 'Lead' && doc.lead)
		cur_frm.cscript.lead(doc, cdt, cdn);
}

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

cur_frm.cscript.lead = function(doc, cdt, cdn) {
	cur_frm.toggle_display("contact_info", doc.customer || doc.lead);
	erpnext.utils.map_current_doc({
		method: "erpnext.crm.doctype.lead.lead.make_opportunity",
		source_name: cur_frm.doc.lead,
		frm: cur_frm
	});
}

cur_frm.cscript['Declare Opportunity Lost'] = function() {
	var dialog = new frappe.ui.Dialog({
		title: __("Set as Lost"),
		fields: [
			{"fieldtype": "Text", "label": __("Reason for losing"), "fieldname": "reason",
				"reqd": 1 },
			{"fieldtype": "Button", "label": __("Update"), "fieldname": "update"},
		]
	});

	dialog.fields_dict.update.$input.click(function() {
		var args = dialog.get_values();
		if(!args) return;
		return cur_frm.call({
			doc: cur_frm.doc,
			method: "declare_enquiry_lost",
			args: args.reason,
			callback: function(r) {
				if(r.exc) {
					frappe.msgprint(__("There were errors."));
				} else {
					dialog.hide();
					cur_frm.refresh();
				}
			},
			btn: this
		})
	});
	dialog.show();
}
