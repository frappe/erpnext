// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}
{% include 'erpnext/selling/quotation_common.js' %}


erpnext.selling.QuotationController = erpnext.selling.SellingController.extend({
	setup: function() {
		this._super();

		this.frm.custom_make_buttons = {
			'Sales Order': 'Sales Order',
			'Sales Invoice': 'Sales Invoice',
			'Auto Repeat': 'Subscription',
		};

		this.setup_queries();
	},

	refresh: function(doc, dt, dn) {
		this._super(doc, dt, dn);

		this.set_dynamic_link();

		var me = this;

		if (me.frm.doc.__islocal && !me.frm.doc.valid_till && !cint(me.frm.doc.quotation_validity_days)) {
			if(frappe.boot.sysdefaults.quotation_valid_till) {
				this.frm.set_value('quotation_validity_days', cint(frappe.boot.sysdefaults.quotation_valid_till));
			} else {
				this.frm.set_value('valid_till', frappe.datetime.add_months(doc.transaction_date, 1));
			}
		}

		this.setup_buttons();
		this.toggle_reqd_lead_customer();
		this.set_dynamic_field_label();
	},

	setup_queries: function () {
		this._super();

		var me = this;

		me.frm.set_query("quotation_to", function() {
			return {
				filters: {
					"name": ["in", ["Customer", "Lead"]],
				}
			}
		});

		me.frm.set_query('party_name', function () {
			if (me.frm.doc.quotation_to == "Lead") {
				return erpnext.queries.lead();
			} else {
				return erpnext.queries.customer();
			}
		});

		me.frm.set_query('customer_address', me.address_query);
		me.frm.set_query('shipping_address_name', me.address_query);
	},

	set_dynamic_link: function () {
		var doctype = this.frm.doc.quotation_to == 'Lead' ? 'Lead' : 'Customer';
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'party_name', doctype: doctype}
	},

	setup_buttons: function () {
		var me = this;

		if (me.frm.doc.docstatus == 0) {
			me.add_get_latest_price_button();
		}
		if (me.frm.doc.docstatus == 1) {
			me.add_update_price_list_button();
		}

		var customer;
		if (me.frm.doc.quotation_to == "Customer") {
			customer = me.frm.doc.party_name;
		} else if (me.frm.doc.quotation_to == "Lead") {
			customer = me.frm.doc.__onload && me.frm.doc.__onload.customer;
		}

		if(me.frm.doc.docstatus == 1 && me.frm.doc.status !== 'Lost') {
			if (me.frm.doc.status !== "Ordered") {
				me.frm.add_custom_button(__('Set as Lost'), () => {
					me.frm.events.set_as_lost_dialog(me.frm);
				}, __("Status"));
			}

			if (!customer) {
				me.frm.add_custom_button(__('Customer'), () => {
					erpnext.utils.make_customer_from_lead(me.frm, me.frm.doc.party_name);
				}, __('Create'));
			}

			if (!me.frm.doc.valid_till || frappe.datetime.get_diff(me.frm.doc.valid_till, frappe.datetime.get_today()) >= 0) {
				me.frm.add_custom_button(__('Sales Order'), () => me.make_sales_order(),
					__('Create'));
				me.frm.add_custom_button(__('Sales Invoice'), () => me.make_sales_invoice(),
					__('Create'));
			}

			if (!me.frm.doc.auto_repeat) {
				me.frm.add_custom_button(__('Subscription'), function() {
					erpnext.utils.make_subscription(me.frm.doc.doctype, me.frm.doc.name)
				}, __('Create'))
			}

			me.frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if (me.frm.doc.status == "Lost") {
			me.frm.add_custom_button(__("Reopen"), () => {
				me.frm.events.update_lost_status(me.frm, false);
			}, __("Status"));
		}

		if (me.frm.doc.docstatus === 0) {
			me.frm.add_custom_button(__('Opportunity'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
						source_doctype: "Opportunity",
						target: me.frm,
						setters: [
							{
								label: "Party",
								fieldname: "party_name",
								fieldtype: "Link",
								options: me.frm.doc.quotation_to,
								default: me.frm.doc.party_name || undefined
							},
							{
								label: "Opportunity Type",
								fieldname: "opportunity_type",
								fieldtype: "Link",
								options: "Opportunity Type",
								default: me.frm.doc.order_type || undefined
							}
						],
						get_query_filters: {
							status: ["not in", ["Lost", "Closed"]],
							company: me.frm.doc.company
						}
					})
				}, __("Get Items From"), "btn-default");

			me.add_get_applicable_items_button();
			me.add_get_project_template_items_button();
		}
	},

	set_dynamic_field_label: function(){
		if (this.frm.doc.quotation_to) {
			this.frm.set_df_property("party_name", "label", __(this.frm.doc.quotation_to));
			this.frm.set_df_property("customer_address", "label", __(this.frm.doc.quotation_to + " Address"));
		}
	},

	toggle_reqd_lead_customer: function() {
		// to overwrite the customer_filter trigger from queries.js
		this.frm.toggle_reqd("party_name", this.frm.doc.quotation_to);
	},

	quotation_to: function() {
		this.toggle_reqd_lead_customer();
		this.set_dynamic_field_label();
		this.set_dynamic_link();
	},

	party_name: function() {
		var me = this;

		if(me.frm.doc.quotation_to=="Lead" && me.frm.doc.party_name) {
			me.get_lead_details();
		}

		return erpnext.utils.get_party_details(this.frm, null, null, function(r) {
			me.apply_price_list();
		});
	},

	tc_name: function() {
		this.get_terms();
	},

	address_query: function(doc) {
		return {
			query: 'frappe.contacts.doctype.address.address.address_query',
			filters: {
				link_doctype: frappe.dynamic_link.doctype,
				link_name: doc.party_name
			}
		};
	},

	validate_company_and_party: function(party_field) {
		if(!this.frm.doc.quotation_to) {
			frappe.msgprint(__("Please select a value for {0} quotation_to {1}", [this.frm.doc.doctype, this.frm.doc.name]));
			return false;
		} else if (this.frm.doc.quotation_to == "Lead") {
			return true;
		} else {
			return this._super(party_field);
		}
	},

	get_lead_details: function() {
		var me = this;
		if(!this.frm.doc.quotation_to === "Lead") {
			return;
		}

		frappe.call({
			method: "erpnext.crm.doctype.lead.lead.get_lead_details",
			args: {
				'lead': this.frm.doc.party_name,
				'posting_date': this.frm.doc.transaction_date,
				'company': this.frm.doc.company,
			},
			callback: function(r) {
				if(r.message) {
					me.frm.updating_party_details = true;
					me.frm.set_value(r.message);
					me.frm.refresh();
					me.frm.updating_party_details = false;

				}
			}
		})
	},

	make_sales_order: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
			frm: cur_frm
		})
	},

	make_sales_invoice: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.quotation.quotation.make_sales_invoice",
			frm: cur_frm
		})
	},
});

cur_frm.script_manager.make(erpnext.selling.QuotationController);

frappe.ui.form.on("Quotation Item", "stock_balance", function(frm, cdt, cdn) {
	var d = frappe.model.get_doc(cdt, cdn);
	frappe.route_options = {"item_code": d.item_code};
	frappe.set_route("query-report", "Stock Balance");
})
