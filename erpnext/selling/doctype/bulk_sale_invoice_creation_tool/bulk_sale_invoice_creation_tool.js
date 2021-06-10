// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Sale Invoice Creation Tool', {
    onload: function(frm){
         frappe.call({
			method: "get_options",
			doc: frm.doc,
			callback: function(r) {
				frm.set_df_property("name_series", "options", r.message);
			}
		});
		frm.set_value("company",frappe.defaults.get_user_default("Company"));
    },
	refresh: function(frm, dt, dn) {
	    frm.disable_save();
	    frm.set_value("posting_date", frappe.datetime.get_today());
		frm.page.set_primary_action(__('Create Sales Invoice'), () => {
			let btn_primary = frm.page.btn_primary.get(0);
			return frm.call({
				doc: frm.doc,
				freeze: true,
				btn: $(btn_primary),
				method: "create_sales_invoice",
				freeze_message: __("Creating Sales Invoices"),
				callback: (r) => {
					if(!r.exc){
						frappe.msgprint(__("Sales Invoice Created"));
						frm.clear_table("items");
						frm.refresh_fields();
						frm.reload_doc();
					}
				}
			});
		});
        frm.add_custom_button(__('Go to Sales Invoice'),function() {
            frappe.set_route("List", "Sales Invoice");
        });
    
	    frm.add_custom_button(__('Sales Order'),function() {
            erpnext.utils.map_current_doc({
                method: "erpnext.selling.doctype.bulk_sale_invoice_creation_tool.bulk_sale_invoice_creation_tool.make_sales_invoice",
                source_doctype: "Sales Order",
                date_field: "transaction_date",
                target: frm,
                setters: {
                    customer: frm.doc.customer || undefined,
                    customer_name: frm.doc.customer_name || undefined,
                    customer_group: frm.doc.customer_group || undefined,

//                    set_warehouse: frm.doc.set_warehouse || undefined
                },
                get_query_filters: {
                    docstatus: 1,
                    status: ["not in", ["Closed", "On Hold"]],
                    per_billed: ["<", 99.99],
                    company: frm.doc.company
                }
            })
        }, __("Get items from"));

        frm.add_custom_button(__('Quotation'), function() {
            erpnext.utils.map_current_doc({
                method: "erpnext.selling.doctype.bulk_sale_invoice_creation_tool.bulk_sale_invoice_creation_tool.make_sales_invoice_quotation",
                source_doctype: "Quotation",
                date_field: "transaction_date",
                target: frm,
                setters: [{
                    fieldtype: 'Link',
                    label: __('Customer'),
                    options: 'Customer',
                    fieldname: 'party_name',
                    default: frm.doc.customer,
                },
                {
                    fieldtype: 'Data',
                    label: __('Customer Name'),
                    fieldname: 'customer_name',
                    default: frm.doc.customer_name,
                },
                {
                    fieldtype: 'Link',
                    label: __('Customer Group'),
                    options: 'Customer Group',
                    fieldname: 'customer_group',
                    default: frm.doc.customer_group,
                }],
                get_query_filters: {
                    docstatus: 1,
                    status: ["!=", "Lost"],
                    company: frm.doc.company
                }
            })
        }, __("Get items from"));

        frm.add_custom_button(__('Delivery Note'), function() {
            erpnext.utils.map_current_doc({
                method: "erpnext.selling.doctype.bulk_sale_invoice_creation_tool.bulk_sale_invoice_creation_tool.make_sales_invoice_delivery",
                source_doctype: "Delivery Note",
                target: frm,
                date_field: "posting_date",
                setters: {
                    customer: frm.doc.customer || undefined,
                    customer_name: frm.doc.customer_name || undefined,
                    customer_group: frm.doc.customer_group || undefined,
//                    set_warehouse: frm.doc.set_warehouse || undefined
                },
                get_query: function() {
                    var filters = {
                        docstatus: 1,
                        company: frm.doc.company,
                        is_return: 0
                    };
                    if(frm.doc.customer) filters["customer"] = frm.doc.customer;
                    return {
                        query: "erpnext.controllers.queries.get_delivery_notes_to_be_billed",
                        filters: filters
                    };
                }
            });
        }, __("Get items from"));
	}
});