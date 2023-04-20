// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on('Quotation', {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Sales Order': 'Sales Order'
		},

		frm.set_query("quotation_to", function() {
			return{
				"filters": {
					"name": ["in", ["Customer", "Lead"]],
				}
			}
		});

		frm.set_df_property('packed_items', 'cannot_add_rows', true);
		frm.set_df_property('packed_items', 'cannot_delete_rows', true);

		frm.set_query('company_address', function(doc) {
			if(!doc.company) {
				frappe.throw(__('Please set Company'));
			}

			return {
				query: 'frappe.contacts.doctype.address.address.address_query',
				filters: {
					link_doctype: 'Company',
					link_name: doc.company
				}
			};
		});
	},

	refresh: function(frm) {
		frm.trigger("set_label");
		frm.trigger("set_dynamic_field_label");
	},

	quotation_to: function(frm) {
		frm.trigger("set_label");
		frm.trigger("toggle_reqd_lead_customer");
		frm.trigger("set_dynamic_field_label");
	},

	set_label: function(frm) {
		frm.fields_dict.customer_address.set_label(__(frm.doc.quotation_to + " Address"));
	}
});

erpnext.selling.QuotationController = class QuotationController extends erpnext.selling.SellingController {
	onload(doc, dt, dn) {
		super.onload(doc, dt, dn);
	}
	party_name() {
		var me = this;
		erpnext.utils.get_party_details(this.frm, null, null, function() {
			me.apply_price_list();
		});

		if(me.frm.doc.quotation_to=="Lead" && me.frm.doc.party_name) {
			me.frm.trigger("get_lead_details");
		}
	}
	refresh(doc, dt, dn) {
		super.refresh(doc, dt, dn);
		frappe.dynamic_link = {
			doc: this.frm.doc,
			fieldname: 'party_name',
			doctype: doc.quotation_to == 'Customer' ? 'Customer' : 'Lead',
		};

		var me = this;

		if (doc.__islocal && !doc.valid_till) {
			if(frappe.boot.sysdefaults.quotation_valid_till){
				this.frm.set_value('valid_till', frappe.datetime.add_days(doc.transaction_date, frappe.boot.sysdefaults.quotation_valid_till));
			} else {
				this.frm.set_value('valid_till', frappe.datetime.add_months(doc.transaction_date, 1));
			}
		}

		if (doc.docstatus == 1 && !["Lost", "Ordered"].includes(doc.status)) {
			if (frappe.boot.sysdefaults.allow_sales_order_creation_for_expired_quotation
				|| (!doc.valid_till)
				|| frappe.datetime.get_diff(doc.valid_till, frappe.datetime.get_today()) >= 0) {
					this.frm.add_custom_button(
						__("Sales Order"),
						() => this.make_sales_order(),
						__("Create")
					);
				}

			if(doc.status!=="Ordered") {
				this.frm.add_custom_button(__('Set as Lost'), () => {
						this.frm.trigger('set_as_lost_dialog');
					});
				}

			if(!doc.auto_repeat) {
				cur_frm.add_custom_button(__('Subscription'), function() {
					erpnext.utils.make_subscription(doc.doctype, doc.name)
				}, __('Create'))
			}

			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if (this.frm.doc.docstatus===0) {
			this.frm.add_custom_button(__('Opportunity'),
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
		}

		this.toggle_reqd_lead_customer();

	}

	make_sales_order() {
		var me = this;

		let has_alternative_item = this.frm.doc.items.some((item) => item.is_alternative);
		if (has_alternative_item) {
			this.show_alternative_items_dialog();
		} else {
			frappe.model.open_mapped_doc({
				method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
				frm: me.frm
			});
		}
	}

	set_dynamic_field_label(){
		if (this.frm.doc.quotation_to == "Customer")
		{
			this.frm.set_df_property("party_name", "label", "Customer");
			this.frm.fields_dict.party_name.get_query = null;
		}

		if (this.frm.doc.quotation_to == "Lead")
		{
			this.frm.set_df_property("party_name", "label", "Lead");

			this.frm.fields_dict.party_name.get_query = function() {
				return{	query: "erpnext.controllers.queries.lead_query" }
			}
		}
	}

	toggle_reqd_lead_customer() {
		var me = this;

		// to overwrite the customer_filter trigger from queries.js
		this.frm.toggle_reqd("party_name", this.frm.doc.quotation_to);
		this.frm.set_query('customer_address', this.address_query);
		this.frm.set_query('shipping_address_name', this.address_query);
	}

	tc_name() {
		this.get_terms();
	}

	address_query(doc) {
		return {
			query: 'frappe.contacts.doctype.address.address.address_query',
			filters: {
				link_doctype: frappe.dynamic_link.doctype,
				link_name: doc.party_name
			}
		};
	}

	validate_company_and_party(party_field) {
		if(!this.frm.doc.quotation_to) {
			frappe.msgprint(__("Please select a value for {0} quotation_to {1}", [this.frm.doc.doctype, this.frm.doc.name]));
			return false;
		} else if (this.frm.doc.quotation_to == "Lead") {
			return true;
		} else {
			return super.validate_company_and_party(party_field);
		}
	}

	get_lead_details() {
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
	}

	show_alternative_items_dialog() {
		let me = this;

		const table_fields = [
		{
			fieldtype:"Data",
			fieldname:"name",
			label: __("Name"),
			read_only: 1,
		},
		{
			fieldtype:"Link",
			fieldname:"item_code",
			options: "Item",
			label: __("Item Code"),
			read_only: 1,
			in_list_view: 1,
			columns: 2,
			formatter: (value, df, options, doc) => {
				return doc.is_alternative ? `<span class="indicator yellow">${value}</span>` : value;
			}
		},
		{
			fieldtype:"Data",
			fieldname:"description",
			label: __("Description"),
			in_list_view: 1,
			read_only: 1,
		},
		{
			fieldtype:"Currency",
			fieldname:"amount",
			label: __("Amount"),
			options: "currency",
			in_list_view: 1,
			read_only: 1,
		},
		{
			fieldtype:"Check",
			fieldname:"is_alternative",
			label: __("Is Alternative"),
			read_only: 1,
		}];


		this.data = this.frm.doc.items.filter(
			(item) => item.is_alternative || item.has_alternative_item
		).map((item) => {
			return {
				"name": item.name,
				"item_code": item.item_code,
				"description": item.description,
				"amount": item.amount,
				"is_alternative": item.is_alternative,
			}
		});

		const dialog = new frappe.ui.Dialog({
			title: __("Select Alternative Items for Sales Order"),
			fields: [
				{
					fieldname: "info",
					fieldtype: "HTML",
					read_only: 1
				},
				{
					fieldname: "alternative_items",
					fieldtype: "Table",
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: true,
					reqd: 1,
					data: this.data,
					description: __("Select an item from each set to be used in the Sales Order."),
					get_data: () => {
						return this.data;
					},
					fields: table_fields
				},
			],
			primary_action: function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
					frm: me.frm,
					args: {
						selected_items: dialog.fields_dict.alternative_items.grid.get_selected_children()
					}
				});
				dialog.hide();
			},
			primary_action_label: __('Continue')
		});

		dialog.fields_dict.info.$wrapper.html(
			`<p class="small text-muted">
				<span class="indicator yellow"></span>
				${__("Alternative Items")}
			</p>`
		)
		dialog.show();
	}
};

cur_frm.script_manager.make(erpnext.selling.QuotationController);

frappe.ui.form.on("Quotation Item", "items_on_form_rendered", "packed_items_on_form_rendered", function(frm, cdt, cdn) {
	// enable tax_amount field if Actual
})

frappe.ui.form.on("Quotation Item", "stock_balance", function(frm, cdt, cdn) {
	var d = frappe.model.get_doc(cdt, cdn);
	frappe.route_options = {"item_code": d.item_code};
	frappe.set_route("query-report", "Stock Balance");
})

frappe.ui.form.on('Quotation', {
	refresh(frm) {
		frm.add_custom_button('Quotation Template', function () { frm.trigger('get_items') }, __("Get Items From"));
	},
	get_items(frm){
		start_quotation_template_dialog(frm);
	}
});

function start_quotation_template_dialog(frm) {

  var transaction_controller = new erpnext.TransactionController({ frm: frm });
	let dialog = new frappe.ui.form.MultiSelectDialog({

		// Read carefully and adjust parameters
		doctype: "Quotation Template", // Doctype we want to pick up
		target: frm,
		setters: {
			// MultiDialog Filterfields
			// customer: frm.doc.customer,
		},
		date_field: "creation", // "modified", "creation", ...
		get_query() {
			// MultiDialog Listfilter
			return {
				filters: {  }
			};
		},
	  action(selections) {
		  for(var n = 0; n < selections.length; n++){
			  var name = selections[n];
			  var items_idx = 0;
			  frappe.db.get_doc("Quotation Template", name) // Again, the Doctype we want to pick up
			  .then(doc => {
				  // Remove the first empty element of the table
				  try {
					  let last = frm.get_field("items").grid.grid_rows.length -1;
					  items_idx = last;
					  if(!('item_code' in frm.get_field("items").grid.grid_rows[last].doc)){
						  frm.get_field("items").grid.grid_rows[0].remove();
						  frm.refresh_fields("items");
					  }
				  } catch (error) {
					  console.log(error);
					  var row=frm.add_child("items"); // add row
					  frm.refresh_fields("items"); // Refresh Tabelle
				  }

				  // Run through all items of the template quotation
				  for(var k = 0; k < doc.quotation_template_item.length; k++){

					  // Declare variables and add table row
					  var item=doc.quotation_template_item[k];
					  var row=frm.add_child("items"); // add row
					  frm.refresh_fields("items"); // Refresh table

					  // Copy-Paste Operation
					for (field of ['item_code', 'qty']) {
						let row = frm.get_field("items").grid.grid_rows[items_idx + 1];
						row.doc[field] = item[field];
						row.refresh_field(field);
					}
					  frm.refresh_fields("items"); // Refresh table

					  // Get all other values from stock etc.
					  let quotation_doc = frm.doc;
					  let cdn = row.name;
					  transaction_controller.item_code(quotation_doc, "Quotation Item", cdn);
					  items_idx++;

				  }
			  });
		  }
	  }
  });
}