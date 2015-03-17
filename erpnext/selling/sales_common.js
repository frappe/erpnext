// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.tax_table = "Sales Taxes and Charges";
{% include 'accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js' %}

frappe.provide("erpnext.selling");
frappe.require("assets/erpnext/js/controllers/transaction.js");

cur_frm.email_field = "contact_email";

erpnext.selling.SellingController = erpnext.TransactionController.extend({
	onload: function() {
		this._super();
		this.setup_queries();
		this.toggle_editable_price_list_rate();
	},

	setup_queries: function() {
		var me = this;

		this.frm.add_fetch("sales_partner", "commission_rate", "commission_rate");

		$.each([["customer_address", "customer_filter"],
			["shipping_address_name", "customer_filter"],
			["contact_person", "customer_filter"],
			["customer", "customer"],
			["lead", "lead"]],
			function(i, opts) {
				if(me.frm.fields_dict[opts[0]])
					me.frm.set_query(opts[0], erpnext.queries[opts[1]]);
			});

		if(this.frm.fields_dict.taxes_and_charges) {
			this.frm.set_query("taxes_and_charges", function() {
				return {
					filters: [
						['Sales Taxes and Charges Master', 'company', '=', me.frm.doc.company],
						['Sales Taxes and Charges Master', 'docstatus', '!=', 2]
					]
				}
			});
		}

		if(this.frm.fields_dict.selling_price_list) {
			this.frm.set_query("selling_price_list", function() {
				return { filters: { selling: 1 } };
			});
		}

		if(!this.frm.fields_dict["items"]) {
			return;
		}

		if(this.frm.fields_dict["items"].grid.get_field('item_code')) {
			this.frm.set_query("item_code", "items", function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: (me.frm.doc.order_type === "Maintenance" ?
						{'is_service_item': 'Yes'}:
						{'is_sales_item': 'Yes'	})
				}
			});
		}

		if(this.frm.fields_dict["items"].grid.get_field('batch_no')) {
			this.frm.set_query("batch_no", "items", function(doc, cdt, cdn) {
				var item = frappe.get_doc(cdt, cdn);
				if(!item.item_code) {
					frappe.throw(__("Please enter Item Code to get batch no"));
				} else {
					filters = {
						'item_code': item.item_code,
						'posting_date': me.frm.doc.posting_date,
					}
					if(item.warehouse) filters["warehouse"] = item.warehouse

					return {
						query : "erpnext.controllers.queries.get_batch_no",
						filters: filters
					}
				}
			});
		}

		if(this.frm.fields_dict.sales_team && this.frm.fields_dict.sales_team.grid.get_field("sales_person")) {
			this.frm.set_query("sales_person", "sales_team", erpnext.queries.not_a_group_filter);
		}
	},

	refresh: function() {
		this._super();
		this.frm.toggle_display("customer_name",
			(this.frm.doc.customer_name && this.frm.doc.customer_name!==this.frm.doc.customer));
		if(this.frm.fields_dict.packed_items) {
			var packing_list_exists = (this.frm.doc.packed_items || []).length;
			this.frm.toggle_display("packing_list", packing_list_exists ? true : false);
		}
	},

	customer: function() {
		var me = this;
		erpnext.utils.get_party_details(this.frm, null, null, function(){me.apply_pricing_rule()});
	},

	customer_address: function() {
		erpnext.utils.get_address_display(this.frm, "customer_address");
	},

	shipping_address_name: function() {
		erpnext.utils.get_address_display(this.frm, "shipping_address_name", "shipping_address");
	},

	contact_person: function() {
		erpnext.utils.get_contact_details(this.frm);
	},

	sales_partner: function() {
		this.apply_pricing_rule();
	},

	campaign: function() {
		this.apply_pricing_rule();
	},

	barcode: function(doc, cdt, cdn) {
		this.item_code(doc, cdt, cdn);
	},

	selling_price_list: function() {
		this.apply_price_list();
	},

	price_list_rate: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		frappe.model.round_floats_in(item, ["price_list_rate", "discount_percentage"]);

		item.rate = flt(item.price_list_rate * (1 - item.discount_percentage / 100.0),
			precision("rate", item));

		this.calculate_taxes_and_totals();
	},

	discount_percentage: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		if(!item.price_list_rate) {
			item.discount_percentage = 0.0;
		} else {
			this.price_list_rate(doc, cdt, cdn);
		}
	},

	commission_rate: function() {
		this.calculate_commission();
		refresh_field("total_commission");
	},

	total_commission: function() {
		if(this.frm.doc.base_net_total) {
			frappe.model.round_floats_in(this.frm.doc, ["base_net_total", "total_commission"]);

			if(this.frm.doc.base_net_total < this.frm.doc.total_commission) {
				var msg = (__("[Error]") + " " +
					__(frappe.meta.get_label(this.frm.doc.doctype, "total_commission",
						this.frm.doc.name)) + " > " +
					__(frappe.meta.get_label(this.frm.doc.doctype, "base_net_total", this.frm.doc.name)));
				msgprint(msg);
				throw msg;
			}

			this.frm.set_value("commission_rate",
				flt(this.frm.doc.total_commission * 100.0 / this.frm.doc.base_net_total));
		}
	},

	allocated_percentage: function(doc, cdt, cdn) {
		var sales_person = frappe.get_doc(cdt, cdn);

		if(sales_person.allocated_percentage) {
			sales_person.allocated_percentage = flt(sales_person.allocated_percentage,
				precision("allocated_percentage", sales_person));
			sales_person.allocated_amount = flt(this.frm.doc.base_net_total *
				sales_person.allocated_percentage / 100.0,
				precision("allocated_amount", sales_person));

			refresh_field(["allocated_percentage", "allocated_amount"], sales_person.name,
				sales_person.parentfield);
		}
	},

	warehouse: function(doc, cdt, cdn) {
		var me = this;
		this.batch_no(doc, cdt, cdn);
		var item = frappe.get_doc(cdt, cdn);
		if(item.item_code && item.warehouse) {
			return this.frm.call({
				method: "erpnext.stock.get_item_details.get_available_qty",
				child: item,
				args: {
					item_code: item.item_code,
					warehouse: item.warehouse,
				},
			});
		}
	},

	toggle_editable_price_list_rate: function() {
		var df = frappe.meta.get_docfield(this.frm.doc.doctype + " Item", "price_list_rate", this.frm.doc.name);
		var editable_price_list_rate = cint(frappe.defaults.get_default("editable_price_list_rate"));

		if(df && editable_price_list_rate) {
			df.read_only = 0;
		}
	},

	calculate_outstanding_amount: function(update_paid_amount) {
		// NOTE:
		// paid_amount and write_off_amount is only for POS Invoice
		// total_advance is only for non POS Invoice
		if(this.frm.doc.doctype == "Sales Invoice" && this.frm.doc.docstatus==0) {
			frappe.model.round_floats_in(this.frm.doc, ["base_grand_total", "total_advance", "write_off_amount",
				"paid_amount"]);
			var total_amount_to_pay = this.frm.doc.base_grand_total - this.frm.doc.write_off_amount
				- this.frm.doc.total_advance;
			if(this.frm.doc.is_pos) {
				if(!this.frm.doc.paid_amount || update_paid_amount===undefined || update_paid_amount) {
					this.frm.doc.paid_amount = flt(total_amount_to_pay);
					this.frm.refresh_field("paid_amount");
				}
			} else {
				this.frm.doc.paid_amount = 0
				this.frm.refresh_field("paid_amount");
			}

			this.frm.set_value("outstanding_amount", flt(total_amount_to_pay
				- this.frm.doc.paid_amount, precision("outstanding_amount")));
		}
	},

	calculate_commission: function() {
		if(this.frm.fields_dict.commission_rate) {
			if(this.frm.doc.commission_rate > 100) {
				var msg = __(frappe.meta.get_label(this.frm.doc.doctype, "commission_rate", this.frm.doc.name)) +
					" " + __("cannot be greater than 100");
				msgprint(msg);
				throw msg;
			}

			this.frm.doc.total_commission = flt(this.frm.doc.base_net_total * this.frm.doc.commission_rate / 100.0,
				precision("total_commission"));
		}
	},

	calculate_contribution: function() {
		var me = this;
		$.each(this.frm.doc.doctype.sales_team || [], function(i, sales_person) {
				frappe.model.round_floats_in(sales_person);
				if(sales_person.allocated_percentage) {
					sales_person.allocated_amount = flt(
						me.frm.doc.base_net_total * sales_person.allocated_percentage / 100.0,
						precision("allocated_amount", sales_person));
				}
			});
	},

	shipping_rule: function() {
		var me = this;
		if(this.frm.doc.shipping_rule) {
			return this.frm.call({
				doc: this.frm.doc,
				method: "apply_shipping_rule",
				callback: function(r) {
					if(!r.exc) {
						me.calculate_taxes_and_totals();
					}
				}
			})
		}
	},

	batch_no: function(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
	    return this.frm.call({
	        method: "erpnext.stock.get_item_details.get_batch_qty",
	        child: item,
	        args: {
	           "batch_no": item.batch_no,
	           "warehouse": item.warehouse,
	           "item_code": item.item_code
	        },
	         "fieldname": "actual_batch_qty"
	    });
	},

	set_dynamic_labels: function() {
		this._super();
		this.set_sales_bom_help(this.frm.doc);
	},

	set_sales_bom_help: function(doc) {
		if(!cur_frm.fields_dict.packing_list) return;
		if ((doc.packed_items || []).length) {
			$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(true);

			if (inList(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
				help_msg = "<div class='alert alert-warning'>" +
					__("For 'Sales BOM' items, Warehouse, Serial No and Batch No will be considered from the 'Packing List' table. If Warehouse and Batch No are same for all packing items for any 'Sales BOM' item, those values can be entered in the main Item table, values will be copied to 'Packing List' table.")+
				"</div>";
				frappe.meta.get_docfield(doc.doctype, 'sales_bom_help', doc.name).options = help_msg;
			}
		} else {
			$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(false);
			if (inList(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
				frappe.meta.get_docfield(doc.doctype, 'sales_bom_help', doc.name).options = '';
			}
		}
		refresh_field('sales_bom_help');
	}
});

frappe.ui.form.on(cur_frm.doctype,"project_name", function(frm) {
	if(in_list(["Delivery Note", "Sales Invoice"], frm.doc.doctype)) {
		frappe.call({
			method:'erpnext.projects.doctype.project.project.get_cost_center_name' ,
			args: {	project_name: frm.doc.project_name	},
			callback: function(r, rt) {
				if(!r.exc) {
					$.each(frm.doc["items"] || [], function(i, row) {
						frappe.model.set_value(row.doctype, row.name, "cost_center", r.message);
						msgprint(__("Cost Center For Item with Item Code '"+row.item_name+"' has been Changed to "+ r.message));
					})
				}
			}
		})
	}
})
