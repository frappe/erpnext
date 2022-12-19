// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}
{% include 'erpnext/selling/quotation_common.js' %}
{% include 'erpnext/stock/applies_to_common.js' %}

frappe.provide("erpnext.crm");

erpnext.crm.Opportunity = frappe.ui.form.Controller.extend({
	setup: function() {
		this.frm.custom_make_buttons = {
			'Customer': 'Customer',
			'Quotation': 'Quotation',
			'Vehicle Quotation': 'Vehicle Quotation',
			'Vehicle Booking Order': 'Vehicle Booking Order',
			'Supplier Quotation': 'Supplier Quotation',
		};

		this.frm.email_field = 'contact_email';
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
			if(me.frm.perm[0].write) {

				me.frm.add_custom_button(__('Schedule Follow Up'), () => this.schedule_follow_up(),
					__("Communication"));

				me.frm.add_custom_button(__('Submit Communication'), () => this.submit_communication(),
					__("Communication"));

				if (me.frm.doc.status !== "Quotation") {
					me.frm.add_custom_button(__('Lost'), () => me.frm.events.set_as_lost_dialog(me.frm),
						__("Status"));
				}

				if (me.frm.doc.status === "Open") {
					me.frm.add_custom_button(__("Close"), () => {
						me.frm.set_value("status", "Closed");
						me.frm.save();
					}, __("Status"));
				} else {
					me.frm.add_custom_button(__("Reopen"), () => {
						me.frm.set_value("lost_reasons", [])
						me.frm.set_value("status", "Open");
						me.frm.save();
					}, __("Status"));
				}
			}

			if(me.frm.doc.status !== "Lost") {
				if(!me.frm.doc.__onload.customer) {
					me.frm.add_custom_button(__('Customer'), () => me.create_customer(),
						__('Create'));
				}

				if (frappe.boot.active_domains.includes("Vehicles")) {
					me.frm.add_custom_button(__("Vehicle Quotation"), () => me.make_vehicle_quotation(),
						__('Create'));
					me.frm.add_custom_button(__("Vehicle Booking Order"), () => me.make_vehicle_booking_order(),
						__('Create'));
				}

				me.frm.add_custom_button(__('Quotation'), () => me.create_quotation(),
					__('Create'));

				if (me.frm.doc.items && me.frm.doc.items.length) {
					me.frm.add_custom_button(__('Supplier Quotation'), () => me.make_supplier_quotation(),
						__('Create'));
				}

				me.frm.page.set_inner_btn_group_as_primary(__("Create"));
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
			if (me.frm.doc.appointment_for === "Customer") {
				return erpnext.queries.customer();
			} else if (me.frm.doc.appointment_for === "Lead") {
				return erpnext.queries.lead();
			}
		});

		me.frm.set_query('customer_address', erpnext.queries.address_query);
		me.frm.set_query('contact_person', erpnext.queries.contact_query)

		me.frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {'is_sales_item': 1}
			};
		});

		if(me.frm.fields_dict["items"].grid.get_field('vehicle_color')) {
			me.frm.set_query("vehicle_color", "items", function(doc, cdt, cdn) {
				var row = frappe.get_doc(cdt, cdn);
				return erpnext.queries.vehicle_color({item_code: row.item_code});
			});
		}

		if (me.frm.fields_dict.delivery_period) {
			me.frm.set_query("delivery_period", function () {
				if (me.frm.doc.transaction_date) {
					return {
						filters: {to_date: [">=", me.frm.doc.transaction_date]}
					}
				}
			});
		}
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
		this.frm.set_value("party_name", "");
	},

	contact_person: function() {
		return erpnext.utils.get_contact_details(this.frm);
	},

	customer_address: function() {
		erpnext.utils.get_address_display(this.frm, 'customer_address', 'address_display', false);
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

	schedule_follow_up: function() {
		var me = this;

		var dialog = new frappe.ui.Dialog({
			title: __('Schedule a Follow Up'),
			doc: {},
			fields: [
				{
					label : "Follow Up in Days",
					fieldname: "follow_up_days",
					fieldtype: "Int",
					default: 0,
					onchange: () => {
						let today = frappe.datetime.nowdate();
						let contact_date = frappe.datetime.add_days(today, dialog.get_value('follow_up_days'));
						dialog.set_value('schedule_date', contact_date)
					}
				},
				{
					fieldtype: "Column Break"
				},
				{
					label : "Schedule Date",
					fieldname: "schedule_date",
					fieldtype: "Date",
					reqd: 1,
					onchange: () => {
						var today = frappe.datetime.get_today();
						var schedule_date = dialog.get_value('schedule_date');
						dialog.doc.follow_up_days = frappe.datetime.get_diff(schedule_date, today);
						dialog.get_field('follow_up_days').refresh();
					}
				},
				{
					fieldtype: "Section Break"
				},
				{
					label : "To Discuss",
					fieldname: "to_discuss",
					fieldtype: "Small Text",
				},
			],
			primary_action: function() {
				var data = dialog.get_values();
				me.frm.add_child('contact_schedule', data);
				me.frm.refresh();
				dialog.hide();
			},
			primary_action_label: __('Schedule')
		});
		dialog.show();
	},

	submit_communication: function() {
		this.frm.check_if_unsaved();

		var me = this;
		var row = this.frm.doc.contact_schedule.find(element => !element.contact_date);

		var d = new frappe.ui.Dialog({
			title: __('Submit Follow Up'),
			fields: [
				{
					"label" : "Schedule Date",
					"fieldname": "schedule_date",
					"fieldtype": "Date",
					"default": row && row.schedule_date,
					"read_only": 1
				},
				{
					fieldtype: "Column Break"
				},
				{
					"label" : "Contact Date",
					"fieldname": "contact_date",
					"fieldtype": "Date",
					"reqd": 1,
					"default": frappe.datetime.nowdate()
				},
				{
					fieldtype: "Section Break"
				},
				{
					"label" : "To Discuss",
					"fieldname": "to_discuss",
					"fieldtype": "Small Text",
					"default": row && row.to_discuss,
					"read_only": 1
				},
				{
					"label" : "Remarks",
					"fieldname": "remarks",
					"fieldtype": "Small Text",
					"reqd": 1
				},
			],
			primary_action: function() {
				var data = d.get_values();
				
				frappe.call({
					method: "erpnext.crm.doctype.opportunity.opportunity.submit_communication",
					args: {
						name: me.frm.doc.name,
						contact_date: data.contact_date,
						remarks: data.remarks
					},
					callback: function (r) {
						if (!r.exc) {
							me.frm.reload_doc();
						}
					}
				});
				d.hide();
			},
			primary_action_label: __('Submit')
		});
		d.show();
	},

	create_customer: function () {
		erpnext.utils.make_customer_from_lead(this.frm, this.frm.doc.party_name);
	},

	create_quotation: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
			frm: this.frm
		})
	},

	make_vehicle_quotation: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_vehicle_quotation",
			frm: this.frm
		})
	},

	make_vehicle_booking_order: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_vehicle_booking_order",
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
