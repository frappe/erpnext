// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


{% include 'erpnext/public/js/controllers/buying.js' %};

cur_frm.add_fetch('contact', 'email_id', 'email_id')

frappe.ui.form.on("Request for Quotation",{
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Supplier Quotation': 'Supplier Quotation'
		}

		frm.fields_dict["suppliers"].grid.get_field("contact").get_query = function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				query: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_supplier_contacts",
				filters: {'supplier': d.supplier}
			}
		}
	},

	onload: function(frm) {
		frm.add_fetch('email_template', 'response', 'message_for_supplier');

		if(!frm.doc.message_for_supplier) {
			frm.set_value("message_for_supplier", __("Please supply the specified items at the best possible rates"))
		}
	},

	refresh: function(frm, cdt, cdn) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Make"),
				function(){ frm.trigger("make_suppplier_quotation") }, __("Supplier Quotation"));

			frm.add_custom_button(__("View"),
				function(){ frappe.set_route('List', 'Supplier Quotation',
					{'request_for_quotation': frm.doc.name}) }, __("Supplier Quotation"));

			frm.add_custom_button(__("Send Supplier Emails"), function() {
				frappe.call({
					method: 'erpnext.buying.doctype.request_for_quotation.request_for_quotation.send_supplier_emails',
					freeze: true,
					args: {
						rfq_name: frm.doc.name
					},
					callback: function(r){
						frm.reload_doc();
					}
				});
			});
		}

	},

	get_suppliers_button: function (frm) {
		var doc = frm.doc;
		var dialog = new frappe.ui.Dialog({
			title: __("Get Suppliers"),
			fields: [
				{	"fieldtype": "Select", "label": __("Get Suppliers By"),
					"fieldname": "search_type",
					"options": "Tag\nSupplier Group", "reqd": 1 },
				{	"fieldtype": "Link", "label": __("Supplier Group"),
					"fieldname": "supplier_group",
					"options": "Supplier Group",	"reqd": 0,
					"depends_on": "eval:doc.search_type == 'Supplier Group'"},
				{	"fieldtype": "Data", "label": __("Tag"),
					"fieldname": "tag",	"reqd": 0,
					"depends_on": "eval:doc.search_type == 'Tag'" },
				{	"fieldtype": "Button", "label": __("Add All Suppliers"),
					"fieldname": "add_suppliers", "cssClass": "btn-primary"},
			]
		});

		dialog.fields_dict.add_suppliers.$input.click(function() {
			var args = dialog.get_values();
			if(!args) return;
			dialog.hide();

			//Remove blanks
			for (var j = 0; j < frm.doc.suppliers.length; j++) {
				if(!frm.doc.suppliers[j].hasOwnProperty("supplier")) {
					frm.get_field("suppliers").grid.grid_rows[j].remove();
				}
			}

			 function load_suppliers(r) {
				if(r.message) {
					for (var i = 0; i < r.message.length; i++) {
						var exists = false;
						if (r.message[i].constructor === Array){
							var supplier = r.message[i][0];
						} else {
							var supplier = r.message[i].name;
						}

						for (var j = 0; j < doc.suppliers.length;j++) {
							if (supplier === doc.suppliers[j].supplier) {
								exists = true;
							}
						}
						if(!exists) {
							var d = frm.add_child('suppliers');
							d.supplier = supplier;
							frm.script_manager.trigger("supplier", d.doctype, d.name);
						}
					}
				}
				frm.refresh_field("suppliers");
			}

			if (args.search_type === "Tag" && args.tag) {
				return frappe.call({
					type: "GET",
					method: "frappe.desk.tags.get_tagged_docs",
					args: {
						"doctype": "Supplier",
						"tag": args.tag
					},
					callback: load_suppliers
				});
			} else if (args.supplier_group) {
				return frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Supplier",
						order_by: "name",
						fields: ["name"],
						filters: [["Supplier", "supplier_group", "=", args.supplier_group]]

					},
					callback: load_suppliers
				});
			}
		});
		dialog.show();

	},
	make_suppplier_quotation: function(frm) {
		var doc = frm.doc;
		var dialog = new frappe.ui.Dialog({
			title: __("For Supplier"),
			fields: [
				{	"fieldtype": "Select", "label": __("Supplier"),
					"fieldname": "supplier",
					"options": doc.suppliers.map(d => d.supplier),
					"reqd": 1 },
				{	"fieldtype": "Button", "label": __("Make Supplier Quotation"),
					"fieldname": "make_supplier_quotation", "cssClass": "btn-primary" },
			]
		});

		dialog.fields_dict.make_supplier_quotation.$input.click(function() {
			var args = dialog.get_values();
			if(!args) return;
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.make_supplier_quotation",
				args: {
					"source_name": doc.name,
					"for_supplier": args.supplier
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			});
		});
		dialog.show()
	}
})

frappe.ui.form.on("Request for Quotation Supplier",{
	supplier: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn]
		frappe.call({
			method:"erpnext.accounts.party.get_party_details",
			args:{
				party: d.supplier,
				party_type: 'Supplier'
			},
			callback: function(r){
				if(r.message){
					frappe.model.set_value(cdt, cdn, 'contact', r.message.contact_person)
					frappe.model.set_value(cdt, cdn, 'email_id', r.message.contact_email)
				}
			}
		})
	},

	download_pdf: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn]

		var w = window.open(
			frappe.urllib.get_full_url("/api/method/erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_pdf?"
			+"doctype="+encodeURIComponent(frm.doc.doctype)
			+"&name="+encodeURIComponent(frm.doc.name)
			+"&supplier_idx="+encodeURIComponent(child.idx)
			+"&no_letterhead=0"));
		if(!w) {
			frappe.msgprint(__("Please enable pop-ups")); return;
		}
	},
	no_quote: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.no_quote) {
			if (d.quote_status != __('Received')) {
				frappe.model.set_value(cdt, cdn, 'quote_status', 'No Quote');
			} else {
				frappe.msgprint(__("Cannot set a received RFQ to No Quote"));
				frappe.model.set_value(cdt, cdn, 'no_quote', 0);
			}
		} else {
			d.quote_status = __('Pending');
			frm.call({
				method:"update_rfq_supplier_status",
				doc: frm.doc,
				args: {
					sup_name: d.supplier
				},
				callback: function(r) {
					frm.refresh_field("suppliers");
				}
			});
		}
	}
})

erpnext.buying.RequestforQuotationController = erpnext.buying.BuyingController.extend({
	refresh: function() {
		var me = this;
		this._super();
		if (this.frm.doc.docstatus===0) {
			this.frm.add_custom_button(__('Material Request'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.stock.doctype.material_request.material_request.make_request_for_quotation",
						source_doctype: "Material Request",
						target: me.frm,
						setters: {
							company: me.frm.doc.company
						},
						get_query_filters: {
							material_request_type: "Purchase",
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_ordered: ["<", 99.99]
						}
					})
				}, __("Get items from"));
			// Get items from Opportunity
            this.frm.add_custom_button(__('Opportunity'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.crm.doctype.opportunity.opportunity.make_request_for_quotation",
						source_doctype: "Opportunity",
						target: me.frm,
						setters: {
							company: me.frm.doc.company
						},
					})
				}, __("Get items from"));
			// Get items from open Material Requests based on supplier
			this.frm.add_custom_button(__('Possible Supplier'), function() {
				// Create a dialog window for the user to pick their supplier
				var d = new frappe.ui.Dialog({
					title: __('Select Possible Supplier'),
					fields: [
					{fieldname: 'supplier', fieldtype:'Link', options:'Supplier', label:'Supplier', reqd:1},
					{fieldname: 'ok_button', fieldtype:'Button', label:'Get Items from Material Requests'},
					]
				});

				// On the user clicking the ok button
				d.fields_dict.ok_button.input.onclick = function() {
					var btn = d.fields_dict.ok_button.input;
					var v = d.get_values();
					if(v) {
						$(btn).set_working();

						erpnext.utils.map_current_doc({
							method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_item_from_material_requests_based_on_supplier",
							source_name: v.supplier,
							target: me.frm,
							setters: {
								company: me.frm.doc.company
							},
							get_query_filters: {
								material_request_type: "Purchase",
								docstatus: 1,
								status: ["!=", "Stopped"],
								per_ordered: ["<", 99.99]
							}
						});
						$(btn).done_working();
						d.hide();
					}
				}
				d.show();
			}, __("Get items from"));

		}
	},

	calculate_taxes_and_totals: function() {
		return;
	},

	tc_name: function() {
		this.get_terms();
	}
});


// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.RequestforQuotationController({frm: cur_frm}));
