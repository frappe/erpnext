// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}
{% include 'erpnext/selling/quotation_common.js' %}

frappe.provide("erpnext.crm");

erpnext.crm.Opportunity = frappe.ui.form.Controller.extend({
	setup: function() {
		this.frm.custom_make_buttons = {
			'Quotation': 'Quotation',
			'Vehicle Quotation': 'Vehicle Quotation',
			'Supplier Quotation': 'Supplier Quotation',
		};

		this.frm.email_field = "contact_email";
	},

	refresh: function() {
		erpnext.hide_company();
		erpnext.toggle_naming_series();
		this.set_dynamic_field_label();
		this.set_dynamic_link();
		this.set_sales_person_from_user();
		this.setup_buttons();
	},

	onload: function() {
		this.setup_queries();
	},

	onload_post_render: function() {
		this.frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	setup_buttons: function() {
		var me = this;

		if (!me.frm.doc.__islocal) {
			if(me.frm.doc.status !== "Lost") {
				me.frm.add_custom_button(__('Quotation'), () => me.create_quotation(),
					__('Create'));

				if(me.frm.doc.items && me.frm.doc.items.length) {
					me.frm.add_custom_button(__('Supplier Quotation'), () => me.make_supplier_quotation(),
					__('Create'));
				}
			}

			if(me.frm.perm[0].write) {
				if (me.frm.doc.status !== "Quotation") {
					me.frm.add_custom_button(__('Lost'), () => me.set_as_lost_dialog());
				}

				if (me.frm.doc.status === "Open") {
					me.frm.add_custom_button(__("Close"), () => {
						me.frm.set_value("status", "Closed");
						me.frm.save();
					});
				} else {
					me.frm.add_custom_button(__("Reopen"), () => {
						me.frm.set_value("lost_reasons",[])
						me.frm.set_value("status", "Open");
						me.frm.save();
					});
				}
			}
		}
	},

	setup_queries: function() {
		var me = this;

		me.frm.set_query("opportunity_from", function() {
			return {
				"filters": {
					"name": ["in", ["Customer", "Lead"]],
				}
			}
		});

		me.frm.set_query('party_name', function() {
			me.frm.set_query("party_name", function () {
				if (me.frm.doc.appointment_for === "Customer") {
					return erpnext.queries.customer();
				} else if (me.frm.doc.appointment_for === "Lead") {
					return erpnext.queries.lead();
				}
			});
		});

		me.frm.set_query('customer_address', erpnext.queries.address_query);
		me.frm.set_query('contact_person', erpnext.queries.contact_query)

		me.frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {'is_sales_item': 1}
			};
		});
	},

	set_dynamic_field_label: function(){
		if (this.frm.doc.opportunity_from) {
			this.frm.set_df_property("party_name", "label", __(this.frm.doc.opportunity_from));
			this.frm.set_df_property("customer_address", "label", __(this.frm.doc.opportunity_from + " Address"));
			this.frm.set_df_property("contact_person", "label", __(this.frm.doc.opportunity_from + " Contact Person"));
		} else {
			this.frm.set_df_property("party_name", "label", __("Party"));
			this.frm.set_df_property("customer_address", "label", __("Address"));
			this.frm.set_df_property("contact_person", "label", __("Contact Person"));
		}
	},

	set_dynamic_link: function() {
		var doctype = this.frm.doc.opportunity_from == 'Lead' ? 'Lead' : 'Customer';
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'party_name', doctype: doctype}
	},

	set_sales_person_from_user: function() {
		if (!this.frm.get_field('sales_person') || this.frm.doc.sales_person || !this.frm.doc.__islocal) {
			return;
		}

		erpnext.utils.get_sales_person_from_user(sales_person => {
			if (sales_person) {
				this.frm.set_value('sales_person', sales_person);
			}
		});
	},

	opportunity_from: function() {
		this.set_dynamic_link();
		this.set_dynamic_field_label();
		this.frm.set_value("party_name","");
	},

	contact_person: function() {
		return erpnext.utils.get_contact_details(this.frm);
	},

	customer_address: function() {
		erpnext.utils.get_address_display(this.frm, 'customer_address', 'address_display', false);
	},

	transaction_date: function() {
		this.set_contact_schedule();
	},

	party_name: function() {
		return this.get_customer_details();
	},

	get_customer_details: function() {
		var me = this;

		if (me.frm.doc.company && me.frm.doc.opportunity_from && me.frm.doc.party_name) {
			return frappe.call({
				method: "erpnext.crm.doctype.opportunity.opportunity.get_customer_details",
				args: {
					args: {
						doctype: me.frm.doc.doctype,
						company: me.frm.doc.company,
						opportunity_from: me.frm.doc.opportunity_from,
						party_name: me.frm.doc.party_name,
					}
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						return me.frm.set_value(r.message);
					}
				}
			});
		}
	},

	item_code: function(doc, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);

		if (d.item_code) {
			return frappe.call({
				method: "erpnext.crm.doctype.opportunity.opportunity.get_item_details",
				args: {
					"item_code": d.item_code
				},
				callback: function(r) {
					if(r.message) {
						$.each(r.message, function(k, v) {
							frappe.model.set_value(cdt, cdn, k, v);
						});
					}
				}
			});
		}
	},

	set_contact_schedule: function() {
		var me = this;
		frappe.db.get_single_value("CRM Settings", "follow_up_period").then((r) => {
			var followups = []
			for (let i = 1; i < 4; i++){
				followups.push({date: frappe.datetime.add_days(this.frm.doc.transaction_date, i*r)});
			}
			me.frm.set_value('contact_schedule', followups);
			me.frm.refresh_field('contact_schedule');
		})
	},

	create_quotation: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
			frm: this.frm
		})
	},

	make_supplier_quotation: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_supplier_quotation",
			frm: this.frm
		})
	},
});

$.extend(cur_frm.cscript, new erpnext.crm.Opportunity({frm: cur_frm}));
