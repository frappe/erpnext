// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.tax_table = "Sales Taxes and Charges";
{% include 'erpnext/accounts/doctype/sales_taxes_and_charges_template/sales_taxes_and_charges_template.js' %}


cur_frm.email_field = "contact_email";

frappe.provide("erpnext.selling");
erpnext.selling.SellingController = class SellingController extends erpnext.TransactionController {
	setup() {
		super.setup();
		this.frm.add_fetch("sales_partner", "commission_rate", "commission_rate");
	}

	onload() {
		super.onload();
		this.setup_queries();
		this.frm.set_query('shipping_rule', function() {
			return {
				filters: {
					"shipping_rule_type": "Selling"
				}
			};
		});
	}

	setup_queries() {
		var me = this;

		var party_queries = [
			["customer", "customer"],
			["bill_to", "customer"],
			["vehicle_owner", "customer"],
			["lead", "lead"]
		];

		$.each(party_queries, function(i, opts) {
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

		if(this.frm.fields_dict.tc_name) {
			this.frm.set_query("tc_name", function() {
				return { filters: { selling: 1 } };
			});
		}

		if(this.frm.fields_dict.transaction_type) {
			this.frm.set_query("transaction_type", function() {
				return { filters: { selling: 1 } };
			});
		}

		if(this.frm.fields_dict.insurance_company) {
			this.frm.set_query("insurance_company", function(doc) {
				return {
					query: "erpnext.controllers.queries.customer_query",
					filters: {is_insurance_company: 1}
				};
			});
		}

		if(this.frm.fields_dict.received_by_type) {
			this.frm.set_query("received_by_type", function(doc) {
				return {filters: {name: ['in', ['Employee', 'Customer', 'Contact']]}};
			});
		}

		if(!this.frm.fields_dict["items"]) {
			return;
		}

		if(this.frm.fields_dict["items"].grid.get_field('item_code')) {
			this.frm.set_query("item_code", "items", function(doc) {
				var filters = {'is_sales_item': 1};
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: filters
				}
			});
		}

		if(this.frm.fields_dict["items"].grid.get_field('vehicle')) {
			this.frm.set_query("vehicle", "items", function(doc, cdt, cdn) {
				var item = frappe.get_doc(cdt, cdn);

				var filters = {};
				if (item.item_code) {
					filters.item_code = item.item_code;
				}

				if (doc.customer) {
					filters['customer'] = ['in', [doc.customer, '']];
				}

				if (doc.doctype === "Delivery Note" || (doc.doctype === "Sales Invoice" && doc.update_stock)) {
					if (doc.is_return) {
						filters['warehouse'] = ['is', 'not set'];
						filters['delivery_document_no'] = ['is', 'set'];
					} else {
						if (item.warehouse) {
							filters['warehouse'] = item.warehouse;
						} else {
							filters['warehouse'] = ['is', 'set'];
						}
					}
				}

				if (item.sales_order) {
					filters['sales_order'] = ['in', [item.sales_order, '']];
				}
				if (doc.doctype === "Sales Invoice" && item.delivery_note) {
					filters['delivery_document_type'] = 'Delivery Note';
					filters['delivery_document_no'] = item.delivery_note;
				}
				return {
					filters: filters
				}
			});
		}

		if(this.frm.fields_dict["packed_items"] &&
			this.frm.fields_dict["packed_items"].grid.get_field('batch_no')) {
			this.frm.set_query("batch_no", "packed_items", function(doc, cdt, cdn) {
				return me.set_query_for_batch(doc, cdt, cdn)
			});
		}

	}

	refresh() {
		super.refresh();

		this.set_dynamic_link();

		if(this.frm.fields_dict.packed_items) {
			var packing_list_exists = (this.frm.doc.packed_items || []).length;
			this.frm.toggle_display("packing_list", packing_list_exists ? true : false);
		}
		this.toggle_editable_price_list_rate();

		var me = this;

		if (me.frm.doc.docstatus === 0) {
			this.create_select_batch_button();
		}
	}

	set_dynamic_link() {
		if (this.frm.doc.bill_to) {
			frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'bill_to', doctype: 'Customer'};
		} else {
			frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'customer', doctype: 'Customer'};
		}
	}

	customer() {
		var me = this;
		return erpnext.utils.get_party_details(this.frm, null, null, function() {
			me.apply_price_list();
		});
	}

	customer_address() {
		erpnext.utils.get_address_display(this.frm, "customer_address");
		erpnext.utils.set_taxes_from_address(this.frm, "customer_address", "customer_address", "shipping_address_name");
	}

	shipping_address_name() {
		erpnext.utils.get_address_display(this.frm, "shipping_address_name", "shipping_address");
		erpnext.utils.set_taxes_from_address(this.frm, "shipping_address_name", "customer_address", "shipping_address_name");
	}

	sales_partner() {
		this.apply_pricing_rule();
	}

	campaign() {
		this.apply_pricing_rule();
	}

	selling_price_list() {
		this.apply_price_list();
		this.set_dynamic_labels();
	}

	price_list_rate(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);

		// check if child doctype is Sales Order Item/Qutation Item and calculate the rate
		if(in_list(["Quotation Item", "Sales Order Item", "Delivery Note Item", "Sales Invoice Item"]), cdt)
			this.apply_pricing_rule_on_item(item);
		else
			item.rate = flt(item.price_list_rate * (1 - item.discount_percentage / 100.0));

		this.calculate_taxes_and_totals();
	}

	default_depreciation_percentage() {
		this.set_default_depreciation(this.frm.doc.default_depreciation_percentage);
	}

	set_default_depreciation(default_depreciation_percentage) {
		var me = this;

		default_depreciation_percentage = flt(default_depreciation_percentage);
		$.each(me.frm.doc.items || [], function (i, d) {
			if (d.is_stock_item) {
				d.depreciation_percentage = default_depreciation_percentage;
			} else {
				d.depreciation_percentage = 0;
			}
		});

		if (this.frm.doc.docstatus === 0) {
			me.calculate_taxes_and_totals();
		} else {
			me.frm.refresh_field('items');
		}
	}

	depreciation_percentage() {
		if (this.frm.doc.docstatus === 0) {
			this.calculate_taxes_and_totals();
		}
	}

	depreciation_type() {
		this.calculate_taxes_and_totals();
	}

	discount_percentage(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		item.discount_amount = 0.0;
		this.apply_discount_on_item(doc, cdt, cdn, 'discount_percentage');
	}

	discount_amount(doc, cdt, cdn) {

		if(doc.name === cdn) {
			return;
		}

		var item = frappe.get_doc(cdt, cdn);
		item.discount_percentage = 0.0;
		this.apply_discount_on_item(doc, cdt, cdn, 'discount_amount');
	}

	apply_discount_on_item(doc, cdt, cdn, field) {
		var item = frappe.get_doc(cdt, cdn);
		if(!item.price_list_rate) {
			item[field] = 0.0;
		} else {
			this.price_list_rate(doc, cdt, cdn);
		}
		this.set_gross_profit(item);
	}

	commission_rate() {
		this.calculate_commission();
		refresh_field("total_commission");
	}

	total_commission() {
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
	}

	sales_team_add() {
		this.calculate_sales_team_contribution();
	}
	allocated_percentage() {
		this.calculate_sales_team_contribution();
	}
	sales_person(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.get_sales_person_details(row);
	}

	warehouse(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);

		let serial_no_count = item.serial_no
			? item.serial_no.split(`\n`).filter(d => d).length : 0;

		if (item.serial_no && item.qty === serial_no_count) {
			return;
		}

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
						has_batch_no: has_batch_no || 0,
						stock_qty: item.stock_qty,
						serial_no: item.serial_no || "",
					},
					callback:function(r){

					}
				});
			}
		})
	}

	toggle_editable_price_list_rate() {
		var df = frappe.meta.get_docfield(this.frm.doc.doctype + " Item", "price_list_rate", this.frm.doc.name);
		var editable_price_list_rate = cint(frappe.defaults.get_default("editable_price_list_rate"));

		if(df && editable_price_list_rate) {
			df.read_only = 0;
		}
	}

	calculate_commission() {
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
	}

	get_sales_person_details(row) {
		var me = this;

		if (!row) {
			return;
		}

		return frappe.call({
			method: 'erpnext.setup.doctype.sales_person.sales_person.get_sales_person_commission_details',
			args: {
				sales_person: row.sales_person
			},
			callback: function (r) {
				if (r.message) {
					frappe.model.set_value(row.doctype, row.name, r.message);
					me.calculate_sales_team_contribution();
				}
			}
		});
	}

	calculate_sales_team_contribution(do_not_refresh) {
		var me = this;
		var net_total = flt(me.frm.doc.base_net_total);

		$.each(this.frm.doc.sales_team || [], function(i, sales_person) {
			frappe.model.round_floats_in(sales_person);

			sales_person.allocated_amount = flt(net_total * sales_person.allocated_percentage / 100.0,
				precision("allocated_amount", sales_person));

			sales_person.incentives = flt(sales_person.allocated_amount * sales_person.commission_rate / 100.0,
				precision("incentives", sales_person));
		});

		if (!do_not_refresh) {
			refresh_field('sales_team');
		}
	}

	batch_no(doc, cdt, cdn) {
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
						"stock_qty": item.stock_qty || item.qty, //if stock_qty field is not available fetch qty (in case of Packed Items table)
						"warehouse": item.warehouse,
						"item_code": item.item_code,
						"has_serial_no": has_serial_no
					},
					"fieldname": "actual_batch_qty"
				});
			}
		})
	}

	set_dynamic_labels() {
		super.set_dynamic_labels();
		this.set_product_bundle_help(this.frm.doc);
	}

	set_product_bundle_help(doc) {
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
	}

	margin_rate_or_amount(doc, cdt, cdn) {
		// calculated the revised total margin and rate on margin rate changes
		var item = locals[cdt][cdn];
		this.apply_pricing_rule_on_item(item)
		this.calculate_taxes_and_totals();
		cur_frm.refresh_fields();
	}

	margin_type(doc, cdt, cdn) {
		// calculate the revised total margin and rate on margin type changes
		var item = locals[cdt][cdn];
		if(!item.margin_type) {
			frappe.model.set_value(cdt, cdn, "margin_rate_or_amount", 0);
		} else {
			this.apply_pricing_rule_on_item(item, doc,cdt, cdn)
			this.calculate_taxes_and_totals();
			cur_frm.refresh_fields();
		}
	}

	company_address() {
		var me = this;
		if(this.frm.doc.company_address) {
			frappe.call({
				method: "erpnext.accounts.party.get_address_display",
				args: {"address": this.frm.doc.company_address },
				callback: function(r) {
					if(r.message) {
						me.frm.set_value("company_address_display", r.message)
					}
				}
			})
		} else {
			this.frm.set_value("company_address_display", "");
		}
	}

	/* Determine appropriate batch number and set it in the form.
	* @param {string} cdt - Document Doctype
	* @param {string} cdn - Document name
	*/
	set_batch_number(cdt, cdn, show_dialog) {
		const doc = frappe.get_doc(cdt, cdn);
		if (doc && frappe.meta.get_docfield(cdt, "stock_qty", cdn)) {
			if (!doc.delivery_note && (this.frm.doc.update_stock || this.frm.doc.doctype != 'Sales Invoice') && !this.frm.doc.is_return) {
				this._set_batch_number(doc, show_dialog);
			}
		}
	}

	_set_batch_number(doc, show_dialog) {
		var me = this;

		if (doc.has_batch_no && frappe.meta.get_docfield(doc.doctype, "batch_no", doc.name)) {
			return frappe.call({
				method: 'erpnext.stock.doctype.batch.batch.get_sufficient_batch_or_fifo',
				args: {
					'item_code': doc.item_code,
					'warehouse': doc.s_warehouse || doc.warehouse,
					'qty': flt(doc.qty),
					'conversion_factor': flt(doc.conversion_factor),
					'sales_order_item': doc.sales_order_item
				},
				callback: function (r) {
					if (r.message) {
						if (r.message.length === 1 && !show_dialog) {
							frappe.model.set_value(doc.doctype, doc.name, 'batch_no', r.message[0].batch_no);
						} else {
							erpnext.show_serial_batch_selector(me.frm, doc, (item) => {
								me.qty(item, item.doctype, item.name, true);
							}, null, 'batch_no', (obj) => {
								obj.set_batch_nos(r.message);
								obj.update_total_qty(doc.qty);
							});
						}
					}
				}
			});
		}
	}

	create_select_batch_button() {
		var me = this;
		this.frm.fields_dict.items.grid.add_custom_button(__("Select Batches"), function() {
			if (me.frm.focused_item_dn) {
				const item = frappe.get_doc(me.frm.doc.doctype + " Item", me.frm.focused_item_dn);
				if (item && !item.delivery_note && (me.frm.doc.update_stock || me.frm.doc.doctype != 'Sales Invoice') && !me.frm.doc.is_return) {
					erpnext.show_serial_batch_selector(me.frm, item, (item) => {
						me.qty(item, item.doctype, item.name);
					}, null, 'batch_no');
				}
			}
		});
		this.frm.fields_dict.items.grid.custom_buttons[__("Select Batches")].addClass('hidden btn-primary');
	}

	auto_select_batches() {
		if ((this.frm.doc.doctype === "Delivery Note" || this.frm.doc.update_stock) && !this.frm.doc.is_return) {
			var me = this;
			return frappe.call({
				method: 'auto_select_batches',
				doc: me.frm.doc,
				freeze: 1,
				callback: function (r) {
					if (!r.exc) {
						me.calculate_taxes_and_totals();
						me.frm.dirty();
					}
				}
			});
		}
	}

	items_row_focused(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.focused_item_dn = row ? row.name : null;
		this.show_hide_select_batch_button();
	}

	show_hide_select_batch_button() {
		var row;
		if (this.frm.focused_item_dn) {
			row = frappe.get_doc(this.frm.doc.doctype + " Item", this.frm.focused_item_dn);
		}

		var update_stock = this.frm.doc.doctype === 'Delivery Note' ||
			(this.frm.doc.doctype === 'Sales Invoice' && this.frm.doc.update_stock);

		var show_select_batch = update_stock
			&& row
			&& row.item_code
			&& row.has_batch_no
			&& this.frm.doc.docstatus === 0
			&& !this.frm.doc.is_return;

		var button = this.frm.fields_dict.items.grid.custom_buttons[__("Select Batches")];
		if (button) {
			if (show_select_batch) {
				button.removeClass('hidden');
			} else {
				button.addClass('hidden');
			}
		}
	}

	to_warehouse() {
		var me = this;
		$.each(this.frm.doc.items || [], function(i, item) {
			frappe.model.set_value(me.frm.doctype + " Item", item.name, "target_warehouse", me.frm.doc.to_warehouse);
		});
	}

	update_auto_repeat_reference(doc) {
		if (doc.auto_repeat) {
			frappe.call({
				method:"frappe.automation.doctype.auto_repeat.auto_repeat.update_reference",
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

	add_set_cost_as_rate_button() {
		var me = this;
		me.frm.add_custom_button(__("Set Rate as Cost"), function() {
			me.set_cost_as_rate();
		}, __("Prices"));
	}

	set_cost_as_rate() {
		var me = this;
		frappe.call({
			method: "set_rate_as_cost",
			doc: me.frm.doc,
			callback: function() {
				me.frm.refresh_fields();
			}
		});
	}
};
