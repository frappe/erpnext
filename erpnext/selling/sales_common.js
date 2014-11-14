// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// Preset
// ------
// cur_frm.cscript.tname - Details table name
// cur_frm.cscript.fname - Details fieldname
// cur_frm.cscript.other_fname - fieldname
// cur_frm.cscript.sales_team_fname - Sales Team fieldname

frappe.provide("erpnext.selling");
frappe.require("assets/erpnext/js/transaction.js");

{% include "public/js/controllers/accounts.js" %}

erpnext.selling.SellingController = erpnext.TransactionController.extend({
	onload: function() {
		this._super();
		this.setup_queries();
		this.toggle_editable_price_list_rate();
	},

	onload_post_render: function() {
		cur_frm.get_field(this.fname).grid.set_multiple_add("item_code", "qty");
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

		if(!this.fname) {
			return;
		}

		if(this.frm.fields_dict[this.fname].grid.get_field('item_code')) {
			this.frm.set_query("item_code", this.fname, function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: (me.frm.doc.order_type === "Maintenance" ?
						{'is_service_item': 'Yes'}:
						{'is_sales_item': 'Yes'	})
				}
			});
		}

		if(this.frm.fields_dict[this.fname].grid.get_field('batch_no')) {
			this.frm.set_query("batch_no", this.fname, function(doc, cdt, cdn) {
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
		if(this.frm.fields_dict.packing_details) {
			var packing_list_exists = (this.frm.doc.packing_details || []).length;
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

	rate: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		frappe.model.round_floats_in(item, ["rate", "price_list_rate"]);

		if(item.price_list_rate) {
			item.discount_percentage = flt((1 - item.rate / item.price_list_rate) * 100.0,
				precision("discount_percentage", item));
		} else {
			item.discount_percentage = 0.0;
		}

		this.calculate_taxes_and_totals();
	},

	discount_amount: function() {
		this.calculate_taxes_and_totals();
	},

	commission_rate: function() {
		this.calculate_commission();
		refresh_field("total_commission");
	},

	total_commission: function() {
		if(this.frm.doc.net_total) {
			frappe.model.round_floats_in(this.frm.doc, ["net_total", "total_commission"]);

			if(this.frm.doc.net_total < this.frm.doc.total_commission) {
				var msg = (__("[Error]") + " " +
					__(frappe.meta.get_label(this.frm.doc.doctype, "total_commission",
						this.frm.doc.name)) + " > " +
					__(frappe.meta.get_label(this.frm.doc.doctype, "net_total", this.frm.doc.name)));
				msgprint(msg);
				throw msg;
			}

			this.frm.set_value("commission_rate",
				flt(this.frm.doc.total_commission * 100.0 / this.frm.doc.net_total));
		}
	},

	allocated_percentage: function(doc, cdt, cdn) {
		var sales_person = frappe.get_doc(cdt, cdn);

		if(sales_person.allocated_percentage) {
			sales_person.allocated_percentage = flt(sales_person.allocated_percentage,
				precision("allocated_percentage", sales_person));
			sales_person.allocated_amount = flt(this.frm.doc.net_total *
				sales_person.allocated_percentage / 100.0,
				precision("allocated_amount", sales_person));

			refresh_field(["allocated_percentage", "allocated_amount"], sales_person.name,
				sales_person.parentfield);
		}
	},

	warehouse: function(doc, cdt, cdn) {
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
		var df = frappe.meta.get_docfield(this.tname, "price_list_rate", this.frm.doc.name);
		var editable_price_list_rate = cint(frappe.defaults.get_default("editable_price_list_rate"));

		if(df && editable_price_list_rate) {
			df.read_only = 0;
		}
	},

	calculate_taxes_and_totals: function(update_paid_amount) {
		this._super();
		this.calculate_total_advance("Sales Invoice", "advance_adjustment_details", update_paid_amount);
		this.calculate_commission();
		this.calculate_contribution();

		// TODO check for custom_recalc in custom scripts of server

		this.frm.refresh_fields();
	},

	calculate_item_values: function() {
		var me = this;

		if (!this.discount_amount_applied) {
			$.each(this.frm.item_doclist, function(i, item) {
				frappe.model.round_floats_in(item);
				item.amount = flt(item.rate * item.qty, precision("amount", item));

				me._set_in_company_currency(item, "price_list_rate", "base_price_list_rate");
				me._set_in_company_currency(item, "rate", "base_rate");
				me._set_in_company_currency(item, "amount", "base_amount");
			});
		}
	},

	determine_exclusive_rate: function() {
		var me = this;
		$.each(me.frm.item_doclist, function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			var cumulated_tax_fraction = 0.0;

			$.each(me.frm.tax_doclist, function(i, tax) {
				tax.tax_fraction_for_current_item = me.get_current_tax_fraction(tax, item_tax_map);

				if(i==0) {
					tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item;
				} else {
					tax.grand_total_fraction_for_current_item =
						me.frm.tax_doclist[i-1].grand_total_fraction_for_current_item +
						tax.tax_fraction_for_current_item;
				}

				cumulated_tax_fraction += tax.tax_fraction_for_current_item;
			});

			if(cumulated_tax_fraction && !me.discount_amount_applied) {
				item.base_amount = flt(
					(item.amount * me.frm.doc.conversion_rate) / (1 + cumulated_tax_fraction),
					precision("base_amount", item));

				item.base_rate = flt(item.base_amount / item.qty, precision("base_rate", item));

				if(item.discount_percentage == 100) {
					item.base_price_list_rate = item.base_rate;
					item.base_rate = 0.0;
				} else {
					item.base_price_list_rate = flt(item.base_rate / (1 - item.discount_percentage / 100.0),
						precision("base_price_list_rate", item));
				}
			}
		});
	},

	get_current_tax_fraction: function(tax, item_tax_map) {
		// Get tax fraction for calculating tax exclusive amount
		// from tax inclusive amount
		var current_tax_fraction = 0.0;

		if(cint(tax.included_in_print_rate)) {
			var tax_rate = this._get_tax_rate(tax, item_tax_map);

			if(tax.charge_type == "On Net Total") {
				current_tax_fraction = (tax_rate / 100.0);

			} else if(tax.charge_type == "On Previous Row Amount") {
				current_tax_fraction = (tax_rate / 100.0) *
					this.frm.tax_doclist[cint(tax.row_id) - 1].tax_fraction_for_current_item;

			} else if(tax.charge_type == "On Previous Row Total") {
				current_tax_fraction = (tax_rate / 100.0) *
					this.frm.tax_doclist[cint(tax.row_id) - 1].grand_total_fraction_for_current_item;
			}
		}

		return current_tax_fraction;
	},

	calculate_net_total: function() {
		var me = this;
		this.frm.doc.net_total = this.frm.doc.net_total_export = 0.0;

		$.each(this.frm.item_doclist, function(i, item) {
			me.frm.doc.net_total += item.base_amount;
			me.frm.doc.net_total_export += item.amount;
		});

		frappe.model.round_floats_in(this.frm.doc, ["net_total", "net_total_export"]);
	},

	calculate_totals: function() {
		var me = this;
		var tax_count = this.frm.tax_doclist.length;

		this.frm.doc.grand_total = flt(tax_count ? this.frm.tax_doclist[tax_count - 1].total : this.frm.doc.net_total);
		this.frm.doc.grand_total_export = flt(this.frm.doc.grand_total / this.frm.doc.conversion_rate);

		this.frm.doc.other_charges_total = flt(this.frm.doc.grand_total - this.frm.doc.net_total,
			precision("other_charges_total"));
		this.frm.doc.other_charges_total_export = flt(this.frm.doc.grand_total_export -
			this.frm.doc.net_total_export + flt(this.frm.doc.discount_amount),
			precision("other_charges_total_export"));

		this.frm.doc.grand_total = flt(this.frm.doc.grand_total, precision("grand_total"));
		this.frm.doc.grand_total_export = flt(this.frm.doc.grand_total_export, precision("grand_total_export"));

		this.frm.doc.rounded_total = Math.round(this.frm.doc.grand_total);
		this.frm.doc.rounded_total_export = Math.round(this.frm.doc.grand_total_export);
	},

	apply_discount_amount: function() {
		var me = this;
		var distributed_amount = 0.0;

		if (this.frm.doc.discount_amount) {
			var grand_total_for_discount_amount = this.get_grand_total_for_discount_amount();
			// calculate item amount after Discount Amount
			if (grand_total_for_discount_amount) {
				$.each(this.frm.item_doclist, function(i, item) {
					distributed_amount = flt(me.frm.doc.discount_amount) * item.base_amount / grand_total_for_discount_amount;
					item.base_amount = flt(item.base_amount - distributed_amount, precision("base_amount", item));
				});

				this.discount_amount_applied = true;
				this._calculate_taxes_and_totals();
			}
		}
	},

	get_grand_total_for_discount_amount: function() {
		var me = this;
		var total_actual_tax = 0.0;
		var actual_taxes_dict = {};

		$.each(this.frm.tax_doclist, function(i, tax) {
			if (tax.charge_type == "Actual")
				actual_taxes_dict[tax.idx] = tax.tax_amount;
			else if (actual_taxes_dict[tax.row_id] !== null) {
				actual_tax_amount = flt(actual_taxes_dict[tax.row_id]) * flt(tax.rate) / 100;
				actual_taxes_dict[tax.idx] = actual_tax_amount;
			}
		});

		$.each(actual_taxes_dict, function(key, value) {
			if (value)
				total_actual_tax += value;
		});

		grand_total_for_discount_amount = flt(this.frm.doc.grand_total - total_actual_tax,
			precision("grand_total"));
		return grand_total_for_discount_amount;
	},

	calculate_outstanding_amount: function(update_paid_amount) {
		// NOTE:
		// paid_amount and write_off_amount is only for POS Invoice
		// total_advance is only for non POS Invoice
		if(this.frm.doc.doctype == "Sales Invoice" && this.frm.doc.docstatus==0) {
			frappe.model.round_floats_in(this.frm.doc, ["grand_total", "total_advance", "write_off_amount",
				"paid_amount"]);
			var total_amount_to_pay = this.frm.doc.grand_total - this.frm.doc.write_off_amount
				- this.frm.doc.total_advance;
			if(this.frm.doc.is_pos) {
				if(!this.frm.doc.paid_amount || update_paid_amount===undefined || update_paid_amount) {
					this.frm.doc.paid_amount = flt(total_amount_to_pay);
				}
			} else {
				this.frm.doc.paid_amount = 0
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

			this.frm.doc.total_commission = flt(this.frm.doc.net_total * this.frm.doc.commission_rate / 100.0,
				precision("total_commission"));
		}
	},

	calculate_contribution: function() {
		var me = this;
		$.each(this.frm.doc.doctype.sales_team || [], function(i, sales_person) {
				frappe.model.round_floats_in(sales_person);
				if(sales_person.allocated_percentage) {
					sales_person.allocated_amount = flt(
						me.frm.doc.net_total * sales_person.allocated_percentage / 100.0,
						precision("allocated_amount", sales_person));
				}
			});
	},

	_cleanup: function() {
		this._super();
		this.frm.doc.in_words = this.frm.doc.in_words_export = "";
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

	set_dynamic_labels: function() {
		this._super();
		this.set_sales_bom_help(this.frm.doc);
	},

	set_sales_bom_help: function(doc) {
		if(!cur_frm.fields_dict.packing_list) return;
		if ((doc.packing_details || []).length) {
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
	},

	change_form_labels: function(company_currency) {
		var me = this;
		var field_label_map = {};

		var setup_field_label_map = function(fields_list, currency) {
			$.each(fields_list, function(i, fname) {
				var docfield = frappe.meta.docfield_map[me.frm.doc.doctype][fname];
				if(docfield) {
					var label = __(docfield.label || "").replace(/\([^\)]*\)/g, "");
					field_label_map[fname] = label.trim() + " (" + currency + ")";
				}
			});
		};
		setup_field_label_map(["net_total", "other_charges_total", "grand_total",
			"rounded_total", "in_words",
			"outstanding_amount", "total_advance", "paid_amount", "write_off_amount"],
			company_currency);

		setup_field_label_map(["net_total_export", "other_charges_total_export", "grand_total_export",
			"rounded_total_export", "in_words_export"], this.frm.doc.currency);

		cur_frm.set_df_property("conversion_rate", "description", "1 " + this.frm.doc.currency
			+ " = [?] " + company_currency)

		if(this.frm.doc.price_list_currency && this.frm.doc.price_list_currency!=company_currency) {
			cur_frm.set_df_property("plc_conversion_rate", "description", "1 " + this.frm.doc.price_list_currency
				+ " = [?] " + company_currency)
		}

		// toggle fields
		this.frm.toggle_display(["conversion_rate", "net_total", "other_charges_total",
			"grand_total", "rounded_total", "in_words"],
			this.frm.doc.currency != company_currency);

		this.frm.toggle_display(["plc_conversion_rate", "price_list_currency"],
			this.frm.doc.price_list_currency != company_currency);

		// set labels
		$.each(field_label_map, function(fname, label) {
			me.frm.fields_dict[fname].set_label(label);
		});
	},

	change_grid_labels: function(company_currency) {
		var me = this;
		var field_label_map = {};

		var setup_field_label_map = function(fields_list, currency, parentfield) {
			var grid_doctype = me.frm.fields_dict[parentfield].grid.doctype;
			$.each(fields_list, function(i, fname) {
				var docfield = frappe.meta.docfield_map[grid_doctype][fname];
				if(docfield) {
					var label = __(docfield.label || "").replace(/\([^\)]*\)/g, "");
					field_label_map[grid_doctype + "-" + fname] =
						label.trim() + " (" + currency + ")";
				}
			});
		}

		setup_field_label_map(["base_rate", "base_price_list_rate", "base_amount"],
			company_currency, this.fname);

		setup_field_label_map(["rate", "price_list_rate", "amount"],
			this.frm.doc.currency, this.fname);

		setup_field_label_map(["tax_amount", "total"], company_currency, "other_charges");

		if(this.frm.fields_dict["advance_allocation_details"]) {
			setup_field_label_map(["advance_amount", "allocated_amount"], company_currency,
				"advance_allocation_details");
		}

		// toggle columns
		var item_grid = this.frm.fields_dict[this.fname].grid;
		var show = (this.frm.doc.currency != company_currency) ||
			((cur_frm.doc.other_charges || []).filter(
					function(d) { return d.included_in_print_rate===1}).length);

		$.each(["base_rate", "base_price_list_rate", "base_amount"], function(i, fname) {
			if(frappe.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, show);
		});

		// set labels
		var $wrapper = $(this.frm.wrapper);
		$.each(field_label_map, function(fname, label) {
			fname = fname.split("-");
			var df = frappe.meta.get_docfield(fname[0], fname[1], me.frm.doc.name);
			if(df) df.label = label;
		});
	}
});

frappe.ui.form.on(cur_frm.doctype,"project_name", function(frm) {
	if(in_list(["Delivery Note", "Sales Invoice"], frm.doc.doctype)) {
		frappe.call({
			method:'erpnext.projects.doctype.project.project.get_cost_center_name' ,
			args: {	project_name: frm.doc.project_name	},
			callback: function(r, rt) {
				if(!r.exc) {
					$.each(frm.doc[cur_frm.cscript.fname] || [], function(i, row) {
						frappe.model.set_value(row.doctype, row.name, "cost_center", r.message);
						msgprint(__("Cost Center For Item with Item Code '"+row.item_name+"' has been Changed to "+ r.message));
					})
				}
			}
		})
	}
})
