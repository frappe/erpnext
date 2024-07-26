// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.buying");
// cur_frm.add_fetch('project', 'cost_center', 'cost_center');

erpnext.buying = {
	setup_buying_controller: function() {
		erpnext.buying.BuyingController = class BuyingController extends erpnext.TransactionController {
			setup() {
				super.setup();
				this.toggle_enable_for_stock_uom("allow_to_edit_stock_uom_qty_for_purchase");
				this.frm.email_field = "contact_email";
			}

			onload(doc, cdt, cdn) {
				this.setup_queries(doc, cdt, cdn);
				super.onload();

				this.frm.set_query('shipping_rule', function() {
					return {
						filters: {
							"shipping_rule_type": "Buying"
						}
					};
				});

				if (this.frm.doc.__islocal
					&& frappe.meta.has_field(this.frm.doc.doctype, "disable_rounded_total")) {

						var df = frappe.meta.get_docfield(this.frm.doc.doctype, "disable_rounded_total");
						var disable = cint(df.default) || cint(frappe.sys_defaults.disable_rounded_total);
						this.frm.set_value("disable_rounded_total", disable);
				}


				// no idea where me is coming from
				if(this.frm.get_field('shipping_address')) {
					this.frm.set_query("shipping_address", () => {
						if(this.frm.doc.customer) {
							return {
								query: 'frappe.contacts.doctype.address.address.address_query',
								filters: { link_doctype: 'Customer', link_name: this.frm.doc.customer }
							};
						} else
							return erpnext.queries.company_address_query(this.frm.doc)
					});
				}
			}

			setup_queries(doc, cdt, cdn) {
				var me = this;

				if(this.frm.fields_dict.buying_price_list) {
					this.frm.set_query("buying_price_list", function() {
						return{
							filters: { 'buying': 1 }
						}
					});
				}

				if(this.frm.fields_dict.tc_name) {
					this.frm.set_query("tc_name", function() {
						return{
							filters: { 'buying': 1 }
						}
					});
				}

				me.frm.set_query('supplier', erpnext.queries.supplier);
				me.frm.set_query('contact_person', erpnext.queries.contact_query);
				me.frm.set_query('supplier_address', erpnext.queries.address_query);

				me.frm.set_query('billing_address', erpnext.queries.company_address_query);
				erpnext.accounts.dimensions.setup_dimension_filters(me.frm, me.frm.doctype);

				this.frm.set_query("item_code", "items", function() {
					if (me.frm.doc.is_subcontracted) {
						var filters = {'supplier': me.frm.doc.supplier};
						if (me.frm.doc.is_old_subcontracting_flow) {
							filters["is_sub_contracted_item"] = 1;
						}
						else {
							filters["is_stock_item"] = 0;
						}

						return{
							query: "erpnext.controllers.queries.item_query",
							filters: filters
						}
					}
					else {
						return{
							query: "erpnext.controllers.queries.item_query",
							filters: { 'supplier': me.frm.doc.supplier, 'is_purchase_item': 1, 'has_variants': 0}
						}
					}
				});


				this.frm.set_query("manufacturer", "items", function(doc, cdt, cdn) {
					const row = locals[cdt][cdn];
					return {
						query: "erpnext.controllers.queries.item_manufacturer_query",
						filters:{ 'item_code': row.item_code }
					}
				});

				if(this.frm.fields_dict["items"].grid.get_field('item_code')) {
					this.frm.set_query("item_tax_template", "items", function(doc, cdt, cdn) {
						return me.set_query_for_item_tax_template(doc, cdt, cdn)
					});
				}
			}

			refresh(doc) {
				frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'supplier', doctype: 'Supplier'};

				this.frm.toggle_display("supplier_name",
					(this.frm.doc.supplier_name && this.frm.doc.supplier_name!==this.frm.doc.supplier));

				if(this.frm.doc.docstatus==0 &&
					(this.frm.doctype==="Purchase Order" || this.frm.doctype==="Material Request")) {
					this.set_from_product_bundle();
				}

				this.toggle_subcontracting_fields();
				super.refresh();
			}

			toggle_subcontracting_fields() {
				if (['Purchase Receipt', 'Purchase Invoice'].includes(this.frm.doc.doctype)) {
					this.frm.fields_dict.supplied_items.grid.update_docfield_property('consumed_qty',
						'read_only', this.frm.doc.__onload && this.frm.doc.__onload.backflush_based_on === 'BOM');

					this.frm.set_df_property('supplied_items', 'cannot_add_rows', 1);
					this.frm.set_df_property('supplied_items', 'cannot_delete_rows', 1);
				}
			}

			supplier() {
				var me = this;
				erpnext.utils.get_party_details(this.frm, null, null, function(){
					me.apply_price_list();
				});
			}

			supplier_address() {
				erpnext.utils.get_address_display(this.frm);
				erpnext.utils.set_taxes_from_address(this.frm, "supplier_address", "supplier_address", "supplier_address");
			}

			buying_price_list() {
				this.apply_price_list();
			}

			discount_percentage(doc, cdt, cdn) {
				var item = frappe.get_doc(cdt, cdn);
				item.discount_amount = 0.0;
				this.price_list_rate(doc, cdt, cdn);
			}

			discount_amount(doc, cdt, cdn) {
				var item = frappe.get_doc(cdt, cdn);
				item.discount_percentage = 0.0;
				this.price_list_rate(doc, cdt, cdn);
			}

			qty(doc, cdt, cdn) {
				if ((doc.doctype == "Purchase Receipt") || (doc.doctype == "Purchase Invoice" && (doc.update_stock || doc.is_return))) {
					this.calculate_received_qty(doc, cdt, cdn)
				}
				super.qty(doc, cdt, cdn);
			}

			rejected_qty(doc, cdt, cdn) {
				this.calculate_received_qty(doc, cdt, cdn)
			}

			calculate_received_qty(doc, cdt, cdn){
				var item = frappe.get_doc(cdt, cdn);
				frappe.model.round_floats_in(item, ["qty", "rejected_qty"]);

				if(!doc.is_return && this.validate_negative_quantity(cdt, cdn, item, ["qty", "rejected_qty"])){ return }

				let received_qty = flt(item.qty + item.rejected_qty, precision("received_qty", item));
				let received_stock_qty = flt(item.conversion_factor, precision("conversion_factor", item)) * flt(received_qty);

				frappe.model.set_value(cdt, cdn, "received_qty", received_qty);
				frappe.model.set_value(cdt, cdn, "received_stock_qty", received_stock_qty);
			}

			batch_no(doc, cdt, cdn) {
				super.batch_no(doc, cdt, cdn);
			}

			validate_negative_quantity(cdt, cdn, item, fieldnames){
				if(!item || !fieldnames) { return }

				var is_negative_qty = false;
				for(var i = 0; i<fieldnames.length; i++) {
					if(item[fieldnames[i]] < 0){
						frappe.msgprint(__("Row #{0}: {1} can not be negative for item {2}", [item.idx,__(frappe.meta.get_label(cdt, fieldnames[i], cdn)), item.item_code]));
						is_negative_qty = true;
						break;
					}
				}

				return is_negative_qty
			}

			warehouse(doc, cdt, cdn) {
				var item = frappe.get_doc(cdt, cdn);
				if(item.item_code && item.warehouse) {
					return this.frm.call({
						method: "erpnext.stock.get_item_details.get_bin_details",
						child: item,
						args: {
							item_code: item.item_code,
							warehouse: item.warehouse,
							company: doc.company,
							include_child_warehouses: true
						}
					});
				}
			}

			project(doc, cdt, cdn) {
				var item = frappe.get_doc(cdt, cdn);
				if(item.project) {
					$.each(this.frm.doc["items"] || [],
						function(i, other_item) {
							if(!other_item.project) {
								other_item.project = item.project;
								refresh_field("project", other_item.name, other_item.parentfield);
							}
						});
				}
			}

			rejected_warehouse(doc, cdt) {
				// trigger autofill_warehouse only if parent rejected_warehouse field is triggered
				if (["Purchase Invoice", "Purchase Receipt"].includes(cdt)) {
					this.autofill_warehouse(doc.items, "rejected_warehouse", doc.rejected_warehouse);
				}
			}

			category(doc, cdt, cdn) {
				// should be the category field of tax table
				if(cdt != doc.doctype) {
					this.calculate_taxes_and_totals();
				}
			}
			add_deduct_tax(doc, cdt, cdn) {
				this.calculate_taxes_and_totals();
			}

			set_from_product_bundle() {
				var me = this;
				this.frm.add_custom_button(__("Product Bundle"), function() {
					erpnext.buying.get_items_from_product_bundle(me.frm);
				}, __("Get Items From"));
			}

			shipping_address(){
				var me = this;
				erpnext.utils.get_address_display(this.frm, "shipping_address",
					"shipping_address_display", true);
			}

			billing_address() {
				erpnext.utils.get_address_display(this.frm, "billing_address",
					"billing_address_display", true);
			}

			tc_name() {
				this.get_terms();
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

			manufacturer(doc, cdt, cdn) {
				const row = locals[cdt][cdn];

				if(row.manufacturer) {
					frappe.call({
						method: "erpnext.stock.doctype.item_manufacturer.item_manufacturer.get_item_manufacturer_part_no",
						args: {
							'item_code': row.item_code,
							'manufacturer': row.manufacturer
						},
						callback: function(r) {
							if (r.message) {
								frappe.model.set_value(cdt, cdn, 'manufacturer_part_no', r.message);
							}
						}
					});
				}
			}

			manufacturer_part_no(doc, cdt, cdn) {
				const row = locals[cdt][cdn];

				if (row.manufacturer_part_no) {
					frappe.model.get_value('Item Manufacturer',
						{
							'item_code': row.item_code,
							'manufacturer': row.manufacturer,
							'manufacturer_part_no': row.manufacturer_part_no
						},
						'name',
						function(data) {
							if (!data) {
								let msg = {
									message: __("Manufacturer Part Number <b>{0}</b> is invalid", [row.manufacturer_part_no]),
									title: __("Invalid Part Number")
								}
								frappe.throw(msg);
							}
						}
					);
				}
			}

			add_serial_batch_bundle(doc, cdt, cdn) {
				let item = locals[cdt][cdn];
				let me = this;

				frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"])
					.then((r) => {
						if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
							item.has_serial_no = r.message.has_serial_no;
							item.has_batch_no = r.message.has_batch_no;
							item.type_of_transaction = item.qty > 0 ? "Inward" : "Outward";
							item.is_rejected = false;

							new erpnext.SerialBatchPackageSelector(
								me.frm, item, (r) => {
									if (r) {
										let qty = Math.abs(r.total_qty);
										if (doc.is_return) {
											qty = qty * -1;
										}

										let update_values = {
											"serial_and_batch_bundle": r.name,
											"use_serial_batch_fields": 0,
											"qty": qty / flt(item.conversion_factor || 1, precision("conversion_factor", item))
										}

										if (r.warehouse) {
											update_values["warehouse"] = r.warehouse;
										}

										frappe.model.set_value(item.doctype, item.name, update_values);
									}
								}
							);
						}
					});
			}

			add_serial_batch_for_rejected_qty(doc, cdt, cdn) {
				let item = locals[cdt][cdn];
				let me = this;

				frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"])
					.then((r) => {
						if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
							item.has_serial_no = r.message.has_serial_no;
							item.has_batch_no = r.message.has_batch_no;
							item.type_of_transaction = item.rejected_qty > 0 ? "Inward" : "Outward";
							item.is_rejected = true;

							new erpnext.SerialBatchPackageSelector(
								me.frm, item, (r) => {
									if (r) {
										let qty = Math.abs(r.total_qty);
										if (doc.is_return) {
											qty = qty * -1;
										}

										let update_values = {
											"serial_and_batch_bundle": r.name,
											"use_serial_batch_fields": 0,
											"rejected_qty": qty / flt(item.conversion_factor || 1, precision("conversion_factor", item))
										}

										if (r.warehouse) {
											update_values["rejected_warehouse"] = r.warehouse;
										}

										frappe.model.set_value(item.doctype, item.name, update_values);
									}
								}
							);
						}
					});
			}
		};
	}
}

erpnext.buying.link_to_mrs = function(frm) {
	frappe.call({
		method: "erpnext.buying.utils.get_linked_material_requests",
		args:{
			items: frm.doc.items.map((item) => item.item_code)
		},
		callback: function(r) {
			if (!r.message || r.message.length == 0) {
				frappe.throw({
					message: __("No pending Material Requests found to link for the given items."),
					title: __("Note")
				});
			}

			var item_length = frm.doc.items.length;
			for (let item of frm.doc.items) {
				var qty = item.qty;
				(r.message[0] || []).forEach(function(d) {
					if (d.qty > 0 && qty > 0 && item.item_code == d.item_code && !item.material_request_item)
					{
						item.material_request = d.mr_name;
						item.material_request_item = d.mr_item;
						var my_qty = Math.min(qty, d.qty);
						qty = qty - my_qty;
						d.qty = d.qty - my_qty;
						item.stock_qty = my_qty*item.conversion_factor;
						item.qty = my_qty;

						frappe.msgprint("Assigning " + d.mr_name + " to " + d.item_code + " (row " + item.idx + ")");
						if (qty > 0)
						{
							frappe.msgprint("Splitting " + qty + " units of " + d.item_code);
							var newrow = frappe.model.add_child(frm.doc, item.doctype, "items");
							item_length++;

							for (var key in item)
							{
								newrow[key] = item[key];
							}

							newrow.idx = item_length;
							newrow["stock_qty"] = newrow.conversion_factor*qty;
							newrow["qty"] = qty;

							newrow["material_request"] = "";
							newrow["material_request_item"] = "";

						}
					}
				});
			}
			refresh_field("items");
		}
	});
}

erpnext.buying.get_default_bom = function(frm) {
	$.each(frm.doc["items"] || [], function(i, d) {
		if (d.item_code && d.bom === "") {
			return frappe.call({
				type: "GET",
				method: "erpnext.stock.get_item_details.get_default_bom",
				args: {
					"item_code": d.item_code,
				},
				callback: function(r) {
					if(r) {
						frappe.model.set_value(d.doctype, d.name, "bom", r.message);
					}
				}
			})
		}
	});
}

erpnext.buying.get_items_from_product_bundle = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: __("Get Items from Product Bundle"),
		fields: [
			{
				"fieldtype": "Link",
				"label": __("Product Bundle"),
				"fieldname": "product_bundle",
				"options":"Product Bundle",
				"reqd": 1
			},
			{
				"fieldtype": "Currency",
				"label": __("Quantity"),
				"fieldname": "quantity",
				"reqd": 1,
				"default": 1
			}
		],
		primary_action_label: 'Get Items',
		primary_action(args){
			if(!args) return;
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.stock.doctype.packed_item.packed_item.get_items_from_product_bundle",
				args: {
					row: {
						item_code: args.product_bundle,
						quantity: args.quantity,
						parenttype: frm.doc.doctype,
						parent: frm.doc.name,
						supplier: frm.doc.supplier,
						currency: frm.doc.currency,
						conversion_rate: frm.doc.conversion_rate,
						price_list: frm.doc.buying_price_list,
						price_list_currency: frm.doc.price_list_currency,
						plc_conversion_rate: frm.doc.plc_conversion_rate,
						company: frm.doc.company,
						is_subcontracted: frm.doc.is_subcontracted,
						transaction_date: frm.doc.transaction_date || frm.doc.posting_date,
						ignore_pricing_rule: frm.doc.ignore_pricing_rule,
						doctype: frm.doc.doctype
					}
				},
				freeze: true,
				callback: function(r) {
					const first_row_is_empty = function(child_table){
						if($.isArray(child_table) && child_table.length > 0) {
							return !child_table[0].item_code;
						}
						return false;
					};

					const remove_empty_first_row = function(frm){
					if (first_row_is_empty(frm.doc.items)){
						frm.doc.items = frm.doc.items.splice(1);
						}
					};

					if(!r.exc && r.message) {
						remove_empty_first_row(frm);
						for (var i=0; i< r.message.length; i++) {
							var d = frm.add_child("items");
							var item = r.message[i];
							for (var key in  item) {
								if (!is_null(item[key]) && key !== "doctype") {
									d[key] = item[key];
								}
							}
							if(frappe.meta.get_docfield(d.doctype, "price_list_rate", d.name)) {
								frm.script_manager.trigger("price_list_rate", d.doctype, d.name);
							}
						}
						frm.refresh_field("items");
					}
				}
			})
		}
	});

	dialog.show();
}
