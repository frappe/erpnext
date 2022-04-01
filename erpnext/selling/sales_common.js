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
		this.frm.add_fetch("sales_person", "commission_rate", "commission_rate");
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

		$.each([["customer", "customer"],
			["lead", "lead"]],
			function(i, opts) {
				if(me.frm.fields_dict[opts[0]])
					me.frm.set_query(opts[0], erpnext.queries[opts[1]]);
			});

		me.frm.set_query('contact_person', erpnext.queries.contact_query);
		me.frm.set_query('customer_address', erpnext.queries.address_query);
		me.frm.set_query('shipping_address_name', erpnext.queries.address_query);
		me.frm.set_query('dispatch_address_name', erpnext.queries.dispatch_address_query);


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

		if(!this.frm.fields_dict["items"]) {
			return;
		}

		if(this.frm.fields_dict["items"].grid.get_field('item_code')) {
			this.frm.set_query("item_code", "items", function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {'is_sales_item': 1, 'customer': cur_frm.doc.customer}
				}
			});
		}

		if(this.frm.fields_dict["packed_items"] &&
			this.frm.fields_dict["packed_items"].grid.get_field('batch_no')) {
			this.frm.set_query("batch_no", "packed_items", function(doc, cdt, cdn) {
				return me.set_query_for_batch(doc, cdt, cdn)
			});
		}

		if(this.frm.fields_dict["items"].grid.get_field('item_code')) {
			this.frm.set_query("item_tax_template", "items", function(doc, cdt, cdn) {
				return me.set_query_for_item_tax_template(doc, cdt, cdn)
			});
		}

	}

	refresh() {
		super.refresh();

		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'customer', doctype: 'Customer'}

		this.frm.toggle_display("customer_name",
			(this.frm.doc.customer_name && this.frm.doc.customer_name!==this.frm.doc.customer));

		this.toggle_editable_price_list_rate();
	}

	customer() {
		var me = this;
		erpnext.utils.get_party_details(this.frm, null, null, function() {
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

	dispatch_address_name() {
		erpnext.utils.get_address_display(this.frm, "dispatch_address_name", "dispatch_address");
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
	}

	total_commission() {
		frappe.model.round_floats_in(this.frm.doc, ["amount_eligible_for_commission", "total_commission"]);

		const { amount_eligible_for_commission } = this.frm.doc;
		if(!amount_eligible_for_commission) return;

		this.frm.set_value(
			"commission_rate", flt(
				this.frm.doc.total_commission * 100.0 / amount_eligible_for_commission
			)
		);
	}

	allocated_percentage(doc, cdt, cdn) {
		var sales_person = frappe.get_doc(cdt, cdn);
		if(sales_person.allocated_percentage) {

			sales_person.allocated_percentage = flt(sales_person.allocated_percentage,
				precision("allocated_percentage", sales_person));

			sales_person.allocated_amount = flt(this.frm.doc.amount_eligible_for_commission *
				sales_person.allocated_percentage / 100.0,
				precision("allocated_amount", sales_person));
				refresh_field(["allocated_amount"], sales_person);

			this.calculate_incentive(sales_person);
			refresh_field(["allocated_percentage", "allocated_amount", "commission_rate","incentives"], sales_person.name,
				sales_person.parentfield);
		}
	}

	sales_person(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.calculate_incentive(row);
		refresh_field("incentives",row.name,row.parentfield);
	}

	warehouse(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);

		// check if serial nos entered are as much as qty in row
		if (item.serial_no) {
			let serial_nos = item.serial_no.split(`\n`).filter(sn => sn.trim()); // filter out whitespaces
			if (item.qty === serial_nos.length) return;
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
						if (in_list(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
							if (doc.doctype === 'Sales Invoice' && (!doc.update_stock)) return;
							if (has_batch_no) {
								me.set_batch_number(cdt, cdn);
								me.batch_no(doc, cdt, cdn);
							}
						}
					}
				});
			}
		})
	}

	toggle_editable_price_list_rate() {
		var df = frappe.meta.get_docfield(this.frm.doc.doctype + " Item", "price_list_rate", this.frm.doc.name);
		var editable_price_list_rate = cint(frappe.defaults.get_default("editable_price_list_rate"));

		if(df && editable_price_list_rate) {
			const parent_field = frappe.meta.get_parentfield(this.frm.doc.doctype, this.frm.doc.doctype + " Item");
			if (!this.frm.fields_dict[parent_field]) return;

			this.frm.fields_dict[parent_field].grid.update_docfield_property(
				'price_list_rate', 'read_only', 0
			);
		}
	}

	calculate_commission() {
		if(!this.frm.fields_dict.commission_rate) return;

		if(this.frm.doc.commission_rate > 100) {
			this.frm.set_value("commission_rate", 100);
			frappe.throw(`${__(frappe.meta.get_label(
				this.frm.doc.doctype, "commission_rate", this.frm.doc.name
			))} ${__("cannot be greater than 100")}`);
		}

		this.frm.doc.amount_eligible_for_commission = this.frm.doc.items.reduce(
			(sum, item) => item.grant_commission ? sum + item.base_net_amount : sum, 0
		)

		this.frm.doc.total_commission = flt(
			this.frm.doc.amount_eligible_for_commission * this.frm.doc.commission_rate / 100.0,
			precision("total_commission")
		);

		refresh_field(["amount_eligible_for_commission", "total_commission"]);
	}

	calculate_contribution() {
		var me = this;
		$.each(this.frm.doc.doctype.sales_team || [], function(i, sales_person) {
			frappe.model.round_floats_in(sales_person);
			if (!sales_person.allocated_percentage) return;

			sales_person.allocated_amount = flt(
				me.frm.doc.amount_eligible_for_commission
				* sales_person.allocated_percentage
				/ 100.0,
				precision("allocated_amount", sales_person)
			);
		});
	}

	calculate_incentive(row) {
		if(row.allocated_amount)
		{
			row.incentives = flt(
					row.allocated_amount * row.commission_rate / 100.0,
					precision("incentives", row));
		}
	}

	batch_no(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);

		if (item.serial_no) {
			return;
		}

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

	company_address() {
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
	}

	conversion_factor(doc, cdt, cdn, dont_fetch_price_list_rate) {
	    super.conversion_factor(doc, cdt, cdn, dont_fetch_price_list_rate);
		if(frappe.meta.get_docfield(cdt, "stock_qty", cdn) &&
			in_list(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
				if (doc.doctype === 'Sales Invoice' && (!doc.update_stock)) return;
				this.set_batch_number(cdt, cdn);
			}
	}

	batch_no(doc, cdt, cdn) {
		super.batch_no(doc, cdt, cdn);
	}

	qty(doc, cdt, cdn) {
		super.qty(doc, cdt, cdn);

		if(in_list(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
			if (doc.doctype === 'Sales Invoice' && (!doc.update_stock)) return;
			this.set_batch_number(cdt, cdn);
		}
	}

	/* Determine appropriate batch number and set it in the form.
	* @param {string} cdt - Document Doctype
	* @param {string} cdn - Document name
	*/
	set_batch_number(cdt, cdn) {
		const doc = frappe.get_doc(cdt, cdn);
		if (doc && doc.has_batch_no && doc.warehouse) {
			this._set_batch_number(doc);
		}
	}

	_set_batch_number(doc) {
		if (doc.batch_no) {
			return
		}

		let args = {'item_code': doc.item_code, 'warehouse': doc.warehouse, 'qty': flt(doc.qty) * flt(doc.conversion_factor)};
		if (doc.has_serial_no && doc.serial_no) {
			args['serial_no'] = doc.serial_no
		}

		return frappe.call({
			method: 'erpnext.stock.doctype.batch.batch.get_batch_no',
			args: args,
			callback: function(r) {
				if(r.message) {
					frappe.model.set_value(doc.doctype, doc.name, 'batch_no', r.message);
				} else {
				    frappe.model.set_value(doc.doctype, doc.name, 'batch_no', r.message);
				}
			}
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
};

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
								frappe.msgprint(__("Cost Center For Item with Item Code {0} has been Changed to {1}", [row.item_name, r.message]));
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
				{
					"fieldtype": "Table MultiSelect",
					"label": __("Lost Reasons"),
					"fieldname": "lost_reason",
					"options": frm.doctype === 'Opportunity' ? 'Opportunity Lost Reason Detail': 'Quotation Lost Reason Detail',
					"reqd": 1
				},
				{
					"fieldtype": "Table MultiSelect",
					"label": __("Competitors"),
					"fieldname": "competitors",
					"options": "Competitor Detail"
				},
				{
					"fieldtype": "Small Text",
					"label": __("Detailed Reason"),
					"fieldname": "detailed_reason"
				},
			],
			primary_action: function() {
				let values = dialog.get_values();

				frm.call({
					doc: frm.doc,
					method: 'declare_enquiry_lost',
					args: {
						'lost_reasons_list': values.lost_reason,
						'competitors': values.competitors ? values.competitors : [],
						'detailed_reason': values.detailed_reason
					},
					callback: function(r) {
						dialog.hide();
						frm.reload_doc();
					},
				});
			},
			primary_action_label: __('Declare Lost')
		});

		dialog.show();
	}
})