// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.tax_table = "Sales Taxes and Charges";
{% include 'erpnext/accounts/doctype/sales_taxes_and_charges_template/sales_taxes_and_charges_template.js' %}


cur_frm.email_field = "contact_email";

frappe.provide("erpnext.selling");
erpnext.selling.SellingController = erpnext.TransactionController.extend({
	setup: function() {
		this._super();
		this.frm.add_fetch("sales_partner", "commission_rate", "commission_rate");
		this.frm.add_fetch("sales_person", "commission_rate", "commission_rate");
	},

	onload: function() {
		this._super();
		this.setup_queries();
		this.frm.set_query('shipping_rule', function() {
			return {
				filters: {
					"shipping_rule_type": "Selling"
				}
			};
		});
	},

	setup_queries: function() {
		var me = this;

		$.each([["customer", "customer"],
			["lead", "lead"]],
			function(i, opts) {
				if(me.frm.fields_dict[opts[0]])
					me.frm.set_query(opts[0], erpnext.queries[opts[1]]);
			});

		me.frm.set_query('contact_person', erpnext.queries.contact_query);
		me.frm.set_query('customer_address', erpnext.queries.address_query);
		me.frm.set_query('shipping_address_name', erpnext.queries.address_query);

		if(this.frm.fields_dict.taxes_and_charges) {
			this.frm.set_query("taxes_and_charges", function() {
				return {
					filters: [
						['Sales Taxes and Charges Template', 'company', '=', me.frm.doc.company],
						['Sales Taxes and Charges Template', 'docstatus', '!=', 2]
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
					filters: {'is_sales_item': 1}
				}
			});
		}

		if(this.frm.fields_dict["packed_items"] &&
			this.frm.fields_dict["packed_items"].grid.get_field('batch_no')) {
			this.frm.set_query("batch_no", "packed_items", function(doc, cdt, cdn) {
				return me.set_query_for_batch(doc, cdt, cdn)
			});
		}
	},

	refresh: function() {
		this._super();

		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'customer', doctype: 'Customer'}

		this.frm.toggle_display("customer_name",
			(this.frm.doc.customer_name && this.frm.doc.customer_name!==this.frm.doc.customer));
		if(this.frm.fields_dict.packed_items) {
			var packing_list_exists = (this.frm.doc.packed_items || []).length;
			this.frm.toggle_display("packing_list", packing_list_exists ? true : false);
		}
		this.toggle_editable_price_list_rate();
	},

	customer: function() {
		var me = this;
		erpnext.utils.get_party_details(this.frm, null, null, function() {
			me.apply_price_list();
		});
	},

	customer_address: function() {
		erpnext.utils.get_address_display(this.frm, "customer_address");
		erpnext.utils.set_taxes_from_address(this.frm, "customer_address", "customer_address", "shipping_address_name");
	},

	shipping_address_name: function() {
		erpnext.utils.get_address_display(this.frm, "shipping_address_name", "shipping_address");
		erpnext.utils.set_taxes_from_address(this.frm, "shipping_address_name", "customer_address", "shipping_address_name");
	},

	sales_partner: function() {
		this.apply_pricing_rule();
	},

	campaign: function() {
		this.apply_pricing_rule();
	},

	selling_price_list: function() {
		this.apply_price_list();
		this.set_dynamic_labels();
	},

	price_list_rate: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		frappe.model.round_floats_in(item, ["price_list_rate", "discount_percentage"]);

		// check if child doctype is Sales Order Item/Qutation Item and calculate the rate
		if(in_list(["Quotation Item", "Sales Order Item", "Delivery Note Item", "Sales Invoice Item"]), cdt)
			this.apply_pricing_rule_on_item(item);
		else
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
		this.set_gross_profit(item);
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
				frappe.msgprint(msg);
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
				refresh_field(["allocated_amount"], sales_person);

			this.calculate_incentive(sales_person);
			refresh_field(["allocated_percentage", "allocated_amount", "commission_rate","incentives"], sales_person.name,
				sales_person.parentfield);
		}
	},

	sales_person: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.calculate_incentive(row);
		refresh_field("incentives",row.name,row.parentfield);
	},

	warehouse: function(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		if (item.serial_no && !item.batch_no) {
			item.serial_no = null;
		}
		var has_batch_no;
		frappe.db.get_value('Item', {'item_code': item.item_code}, 'has_batch_no', (r) => {
			has_batch_no = r && r.has_batch_no;
			if(item.item_code && item.warehouse) {
				return this.frm.call({
					method: "erpnext.stock.get_item_details.get_bin_details_and_serial_nos",
					child: item,
					args: {
						item_code: item.item_code,
						warehouse: item.warehouse,
						has_batch_no: has_batch_no,
						stock_qty: item.stock_qty,
						serial_no: item.serial_no || "",
					},
					callback:function(r){
						if (in_list(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
							me.set_batch_number(cdt, cdn);
							me.batch_no(doc, cdt, cdn);
						}
					}
				});
			}
		})
	},

	toggle_editable_price_list_rate: function() {
		var df = frappe.meta.get_docfield(this.frm.doc.doctype + " Item", "price_list_rate", this.frm.doc.name);
		var editable_price_list_rate = cint(frappe.defaults.get_default("editable_price_list_rate"));

		if(df && editable_price_list_rate) {
			df.read_only = 0;
		}
	},

	calculate_commission: function() {
		if(this.frm.fields_dict.commission_rate) {
			if(this.frm.doc.commission_rate > 100) {
				var msg = __(frappe.meta.get_label(this.frm.doc.doctype, "commission_rate", this.frm.doc.name)) +
					" " + __("cannot be greater than 100");
				frappe.msgprint(msg);
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

	calculate_incentive: function(row) {
		if(row.allocated_amount)
		{
			row.incentives = flt(
					row.allocated_amount * row.commission_rate / 100.0,
					precision("incentives", row));
		}
	},

	batch_no: function(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		item.serial_no = null;
		var has_serial_no;
		frappe.db.get_value('Item', {'item_code': item.item_code}, 'has_serial_no', (r) => {
			has_serial_no = r && r.has_serial_no;
			if(item.warehouse && item.item_code && item.batch_no) {
				return this.frm.call({
					method: "erpnext.stock.get_item_details.get_batch_qty_and_serial_no",
					child: item,
					args: {
						"batch_no": item.batch_no,
						"stock_qty": item.stock_qty,
						"warehouse": item.warehouse,
						"item_code": item.item_code,
						"has_serial_no": has_serial_no
					},
					"fieldname": "actual_batch_qty"
				});
			}
		})
	},

	set_dynamic_labels: function() {
		this._super();
		this.set_product_bundle_help(this.frm.doc);
	},

	set_product_bundle_help: function(doc) {
		if(!cur_frm.fields_dict.packing_list) return;
		if ((doc.packed_items || []).length) {
			$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(true);

			if (in_list(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
				var help_msg = "<div class='alert alert-warning'>" +
					__("For 'Product Bundle' items, Warehouse, Serial No and Batch No will be considered from the 'Packing List' table. If Warehouse and Batch No are same for all packing items for any 'Product Bundle' item, those values can be entered in the main Item table, values will be copied to 'Packing List' table.")+
				"</div>";
				frappe.meta.get_docfield(doc.doctype, 'product_bundle_help', doc.name).options = help_msg;
			}
		} else {
			$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(false);
			if (in_list(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
				frappe.meta.get_docfield(doc.doctype, 'product_bundle_help', doc.name).options = '';
			}
		}
		refresh_field('product_bundle_help');
	},

	margin_rate_or_amount: function(doc, cdt, cdn) {
		// calculated the revised total margin and rate on margin rate changes
		var item = locals[cdt][cdn];
		this.apply_pricing_rule_on_item(item)
		this.calculate_taxes_and_totals();
		cur_frm.refresh_fields();
	},

	margin_type: function(doc, cdt, cdn){
		// calculate the revised total margin and rate on margin type changes
		var item = locals[cdt][cdn];
		if(!item.margin_type) {
			frappe.model.set_value(cdt, cdn, "margin_rate_or_amount", 0);
		} else {
			this.apply_pricing_rule_on_item(item, doc,cdt, cdn)
			this.calculate_taxes_and_totals();
			cur_frm.refresh_fields();
		}
	},

	company_address: function() {
		var me = this;
		if(this.frm.doc.company_address) {
			frappe.call({
				method: "frappe.contacts.doctype.address.address.get_address_display",
				args: {"address_dict": this.frm.doc.company_address },
				callback: function(r) {
					if(r.message) {
						me.frm.set_value("company_address_display", r.message)
					}
				}
			})
		} else {
			this.frm.set_value("company_address_display", "");
		}
	},

	conversion_factor: function(doc, cdt, cdn, dont_fetch_price_list_rate) {
	    this._super(doc, cdt, cdn, dont_fetch_price_list_rate);
		if(frappe.meta.get_docfield(cdt, "stock_qty", cdn) &&
			in_list(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
			this.set_batch_number(cdt, cdn);
		}
	},

	qty: function(doc, cdt, cdn) {
		this._super(doc, cdt, cdn);
		this.set_batch_number(cdt, cdn);
	},

	/* Determine appropriate batch number and set it in the form.
	* @param {string} cdt - Document Doctype
	* @param {string} cdn - Document name
	*/
	set_batch_number: function(cdt, cdn) {
		const doc = frappe.get_doc(cdt, cdn);
		if (doc && doc.has_batch_no && flt(doc.qty)!==0) {
			this._set_batch_number(doc);
		}
	},

	_set_batch_number: function(doc) {
		return frappe.call({
			method: 'erpnext.stock.doctype.batch.batch.get_batch_no',
			args: {'item_code': doc.item_code, 'warehouse': doc.warehouse, 'qty': flt(doc.qty) * flt(doc.conversion_factor)},
			callback: function(r) {
				if(r.message) {
					frappe.model.set_value(doc.doctype, doc.name, 'batch_no', r.message);
				} else {
				    frappe.model.set_value(doc.doctype, doc.name, 'batch_no', r.message);
				}
			}
		});
	},

	update_auto_repeat_reference: function(doc) {
		if (doc.auto_repeat) {
			frappe.call({
				method:"frappe.desk.doctype.auto_repeat.auto_repeat.update_reference",
				args:{
					docname: doc.auto_repeat,
					reference:doc.name
				},
				callback: function(r){
					if (r.message=="success") {
						frappe.show_alert({message:__("Auto repeat document updated"), indicator:'green'});
					} else {
						frappe.show_alert({message:__("An error occurred during the update process"), indicator:'red'});
					}
				}
			})
		}
	}
});

frappe.ui.form.on(cur_frm.doctype,"project", function(frm) {
	if(in_list(["Delivery Note", "Sales Invoice"], frm.doc.doctype)) {
		if(frm.doc.project) {
			frappe.call({
				method:'erpnext.projects.doctype.project.project.get_cost_center_name' ,
				args: {	project: frm.doc.project	},
				callback: function(r, rt) {
					if(!r.exc) {
						$.each(frm.doc["items"] || [], function(i, row) {
							if(r.message) {
								frappe.model.set_value(row.doctype, row.name, "cost_center", r.message);
								frappe.msgprint(__("Cost Center For Item with Item Code '"+row.item_name+"' has been Changed to "+ r.message));
							}
						})
					}
				}
			})
		}
	}
})

frappe.ui.form.on(cur_frm.doctype, {
	set_as_lost_dialog: function(frm) {
		var dialog = new frappe.ui.Dialog({
			title: __("Set as Lost"),
			fields: [
				{"fieldtype": "Table MultiSelect",
				"label": __("Lost Reasons"),
				"fieldname": "lost_reason",
				"options": "Lost Reason Detail",
				"reqd": 1},

				{"fieldtype": "Text", "label": __("Detailed Reason"), "fieldname": "detailed_reason"},
			],
			primary_action: function() {
				var values = dialog.get_values();
				var reasons = values["lost_reason"];
				var detailed_reason = values["detailed_reason"];

				frm.call({
					doc: frm.doc,
					method: 'declare_enquiry_lost',
					args: {
						'lost_reasons_list': reasons,
						'detailed_reason': detailed_reason
					},
					callback: function(r) {
						dialog.hide();
						frm.reload_doc();
					},
				});
				refresh_field("lost_reason");
			},
			primary_action_label: __('Declare Lost')
		});

		dialog.show();
	}
})
