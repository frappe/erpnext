// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on("Sales Order", {
	setup: function(frm) {
		$.extend(frm.cscript, new erpnext.selling.SalesOrderController({frm: frm}));
		frm.custom_make_buttons = {
			'Delivery Note': 'Delivery',
			'Sales Invoice': 'Invoice',
			'Material Request': 'Material Request',
			'Purchase Order': 'Purchase Order'
		}
		frm.add_fetch('customer', 'tax_id', 'tax_id');
	},
	onload: function(frm) {
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});

		frm.set_query('project', function(doc, cdt, cdn) {
			return {
				query: "erpnext.controllers.queries.get_project_name",
				filters: {
					'customer': doc.customer
				}
			}
		});

		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.stock_qty<=doc.delivered_qty) ? "green" : "orange" })

		erpnext.queries.setup_warehouse_query(frm);
	}
});

erpnext.selling.SalesOrderController = erpnext.selling.SellingController.extend({
	refresh: function(doc, dt, dn) {
		var me = this;
		this._super();
		var allow_purchase = false;
		var allow_delivery = false;

		if(doc.docstatus==1) {
			if(doc.status != 'Closed') {

				for (var i in this.frm.doc.items) {
					var item = this.frm.doc.items[i];
					if(item.delivered_by_supplier === 1 || item.supplier){
						if(item.qty > flt(item.ordered_qty)
							&& item.qty > flt(item.delivered_qty)) {
							allow_purchase = true;
						}
					}

					if (item.delivered_by_supplier===0) {
						if(item.qty > flt(item.delivered_qty)) {
							allow_delivery = true;
						}
					}

					if (allow_delivery && allow_purchase) {
						break;
					}
				}

				if (this.frm.has_perm("submit")) {
					// close
					if(flt(doc.per_delivered, 2) < 100 || flt(doc.per_billed) < 100) {
							this.frm.add_custom_button(__('Close'),
								function() { me.close_sales_order() }, __("Status"))
						}
				}

				// delivery note
				if(flt(doc.per_delivered, 2) < 100 && ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1 && allow_delivery) {
					this.frm.add_custom_button(__('Delivery'),
						function() { me.make_delivery_note() }, __("Make"));
					this.frm.add_custom_button(__('Production Order'),
						function() { me.make_production_order() }, __("Make"));

					this.frm.page.set_inner_btn_group_as_primary(__("Make"));
				}

				// sales invoice
				if(flt(doc.per_billed, 2) < 100) {
					this.frm.add_custom_button(__('Invoice'),
						function() { me.make_sales_invoice() }, __("Make"));
				}

				// material request
				if(!doc.order_type || ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1
					&& flt(doc.per_delivered, 2) < 100) {
						this.frm.add_custom_button(__('Material Request'),
							function() { me.make_material_request() }, __("Make"));
				}

				// make purchase order
				if(flt(doc.per_delivered, 2) < 100 && allow_purchase) {
					this.frm.add_custom_button(__('Purchase Order'),
						function() { me.make_purchase_order() }, __("Make"));
				}

				// payment request
				if(flt(doc.per_billed)==0) {
					this.frm.add_custom_button(__('Payment Request'),
						function() { me.make_payment_request() }, __("Make"));
					this.frm.add_custom_button(__('Payment'),
						function() { me.make_payment_entry() }, __("Make"));
				}

				// maintenance
				if(flt(doc.per_delivered, 2) < 100 &&
						["Sales", "Shopping Cart"].indexOf(doc.order_type)===-1) {
					this.frm.add_custom_button(__('Maintenance Visit'),
						function() { me.make_maintenance_visit() }, __("Make"));
					this.frm.add_custom_button(__('Maintenance Schedule'),
						function() { me.make_maintenance_schedule() }, __("Make"));
				}

			} else {
				if (this.frm.has_perm("submit")) {
					// un-close
					this.frm.add_custom_button(__('Re-open'), function() {
						me.frm.cscript.update_status('Re-open', 'Draft')
					}, __("Status"));
				}
			}
		}

		if (this.frm.doc.docstatus===0) {
			this.frm.add_custom_button(__('Quotation'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
						source_doctype: "Quotation",
						target: me.frm,
						setters: {
							customer: me.frm.doc.customer || undefined
						},
						get_query_filters: {
							company: me.frm.doc.company,
							docstatus: 1,
							status: ["!=", "Lost"],
						}
					})
				}, __("Get items from"));
		}

		this.order_type(doc);
	},

	make_production_order() {
		var me = this;
		this.frm.call({
			doc: this.frm.doc,
			method: 'get_production_order_items',
			callback: function(r) {
				if(!r.message.every(function(d) { return !!d.bom })) {
					frappe.msgprint({
						title: __('Production Order not created'),
						message: __('No Items with Bill of Materials to Manufacture'),
						indicator: 'orange'
					});
					return;
				}
				else if(!r.message.every(function(d) { return !!d.pending_qty })) {
					frappe.msgprint({
						title: __('Production Order not created'),
						message: __('Production Order already created for all items with BOM'),
						indicator: 'orange'
					});
					return;
				} else {
					var fields = [
						{fieldtype:'Table', fieldname: 'items',
							description: __('Select BOM and Qty for Production'),
							fields: [
								{fieldtype:'Read Only', fieldname:'item_code',
									label: __('Item Code'), in_list_view:1},
								{fieldtype:'Link', fieldname:'bom', options: 'BOM', reqd: 1,
									label: __('Select BOM'), in_list_view:1, get_query: function(doc) {
										return {filters: {item: doc.item_code}};
									}},
								{fieldtype:'Float', fieldname:'pending_qty', reqd: 1,
									label: __('Qty'), in_list_view:1},
							],
							get_data: function() {
								return r.message
							}
						}
					]
					var d = new frappe.ui.Dialog({
						title: __('Select Items to Manufacture'),
						fields: fields,
						primary_action: function() {
							data = d.get_values();
							me.frm.call({
								method: 'make_production_orders',
								args: {
									items: data,
									company: me.frm.doc.company,
									sales_order: me.frm.docname,
									project: me.frm.project
								},
								freeze: true,
								callback: function(r) {
									if(r.message) {
										frappe.msgprint({
											message: __('Production Orders Created: {0}',
												[r.message.map(function(d) {
													return repl('<a href="#Form/Production Order/%(name)s">%(name)s</a>', {name:d})
												}).join(', ')]),
											indicator: 'green'
										})
									}
									d.hide();
								}
							});
						},
						primary_action_label: __('Make')
					});
					d.show();
				}
			}
		});
	},

	order_type: function() {
		this.frm.toggle_reqd("delivery_date", this.frm.doc.order_type == "Sales");
	},

	tc_name: function() {
		this.get_terms();
	},

	make_material_request: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
			frm: this.frm
		})
	},

	make_delivery_note: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
			frm: this.frm
		})
	},

	make_sales_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			frm: this.frm
		})
	},

	make_maintenance_schedule: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_schedule",
			frm: this.frm
		})
	},

	make_maintenance_visit: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_visit",
			frm: this.frm
		})
	},

	make_purchase_order: function(){
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("For Supplier"),
			fields: [
				{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier",
					"get_query": function () {
						return {
							query:"erpnext.selling.doctype.sales_order.sales_order.get_supplier",
							filters: {'parent': me.frm.doc.name}
						}
					}, "reqd": 1 },
				{"fieldtype": "Button", "label": __("Make Purchase Order"), "fieldname": "make_purchase_order", "cssClass": "btn-primary"},
			]
		});

		dialog.fields_dict.make_purchase_order.$input.click(function() {
			args = dialog.get_values();
			if(!args) return;
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.selling.doctype.sales_order.sales_order.make_purchase_order_for_drop_shipment",
				args: {
					"source_name": me.frm.doc.name,
					"for_supplier": args.supplier
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			})
		});
		dialog.show();
	},
	close_sales_order: function(){
		this.frm.cscript.update_status("Close", "Closed")
	},
	update_status: function(label, status){
		var doc = this.frm.doc;
		frappe.ui.form.is_saving = true;
		frappe.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.update_status",
			args: {status: status, name: doc.name},
			callback: function(r){
				this.frm.reload_doc();
			},
			always: function() {
				frappe.ui.form.is_saving = false;
			}
		});
	},
	on_submit: function(doc, cdt, cdn) {
		if(cint(frappe.boot.notification_settings.sales_order)) {
			this.frm.email_doc(frappe.boot.notification_settings.sales_order_message);
		}
	}
});
