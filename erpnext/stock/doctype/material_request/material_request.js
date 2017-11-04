// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/buying/doctype/purchase_common/purchase_common.js' %};
cur_frm.add_fetch("material_requester", "department", "department");
cur_frm.add_fetch("material_requester", "user_id", "user_id");
frappe.ui.form.on('Material Request', {
    // validate: function(frm) {
    //        if (user_roles.indexOf("Director") != -1 && frm.doc.state == "Approved") {
    //            frm.set_value("workflow_state", "Approved By Director");
    //            frm.disable_save();
    //        }

    //    },
    setup: function(frm) {
        frm.custom_make_buttons = {
            'Stock Entry': 'Issue Material',
            'Purchase Order': 'Purchase Order',
            'Request for Quotation': 'Request for Quotation',
            'Supplier Quotation': 'Supplier Quotation',
            'Production Order': 'Production Order'
        }
    },
    purchase_workflow: function(frm) {
        // frm.set_value("material_requester", undefined);
        frm.clear_table("items");
        refresh_many(['items']);
        frm.set_value("project", undefined);
        frm.toggle_enable("project", frm.doc.purchase_workflow == "Project");
        frm.toggle_reqd("project", frm.doc.purchase_workflow == "Project");
        if (frm.doc.purchase_workflow == "Project") {
            frappe.call({
                method: "get_project_manager",
                doc: frm.doc,
                callback: function(r) {
                    frm.fields_dict['material_requester'].get_query = function() {
                        return {
                            filters: [
                                ['name', 'in', r.message]
                            ]
                        }
                    }
                }
            });
        } else {
            frm.fields_dict['material_requester'].get_query = function() {
                return "";
            }
        }
    },
    material_requester: function(frm) {


    },
    onload: function(frm) {
    	if(cur_frm.doc.__islocal){
	        frappe.call({
	            method: "frappe.client.get_value",
	            args: {
	                doctype: "Employee",
	                fieldname: "name",
	                filters: { "user_id": user }
	            },
	            callback: function(r, rt) {
	                if (r.message.name) {
	                    cur_frm.set_value("material_requester", r.message.name);
	                }
	            }
	        });
    	}
        frm.fields_dict['project'].get_query = function() {
            if (!frm.doc.material_requester) {
                frappe.throw(__("Please select a requester"));
            }
            return {
                filters: {
                    "project_manager": frm.doc.material_requester,
                    "status": "Open"
                }

            }
        }
        // add item, if previous view was item
        erpnext.utils.add_item(frm);

        // formatter for material request item
        frm.set_indicator_formatter('item_code',
                function(doc) { return (doc.qty <= doc.ordered_qty) ? "green" : "orange" }),

            frm.fields_dict["items"].grid.get_field("warehouse").get_query = function(doc, cdt, cdn) {
                return {
                    filters: { 'company': doc.company }
                }
            }
    }
});

frappe.ui.form.on("Material Request Item", {
    "qty": function(frm, doctype, name) {
        var d = locals[doctype][name];
        if (flt(d.qty) < flt(d.min_order_qty)) {
            alert(__("Warning: Material Requested Qty is less than Minimum Order Qty"));
        }
    }
});

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
    onload: function(doc) {
        this._super();
        this.frm.set_query("item_code", "items", function() {
        	var flts = {};
        	if (doc.purchase_workflow == "Asset"){
        		flts = {'is_fixed_asset': 1};
        	}
        	else if (doc.purchase_workflow == "Project"){
        		flts = {'is_fixed_asset': 0};
        	}
            return {
                query: "erpnext.controllers.queries.item_query",
                filters: flts
            }
        });


    },

    refresh: function(doc) {

        for (var key in cur_frm.fields_dict) {
            cur_frm.fields_dict[key].df.read_only = 1;
        }
        cur_frm.disable_save();
        if (cur_frm.doc.__islocal || (cur_frm.doc.state == "Rejected" && cur_frm.doc.user_id == user)) {
            for (var key in cur_frm.fields_dict) {
                cur_frm.fields_dict[key].df.read_only = 0;
            }
            cur_frm.enable_save();
            cur_frm.fields_dict["material_requester"].df.read_only = 1;
            cur_frm.fields_dict["state"].df.read_only = 1;
            cur_frm.fields_dict["suggested_grand_total"].df.read_only = 1;
        }


        var me = this;
        this._super();

        if (doc.docstatus == 0) {
            cur_frm.add_custom_button(__("Get Items from BOM"),
                cur_frm.cscript.get_items_from_bom, "fa fa-sitemap", "btn-default");
        }

        if (doc.docstatus == 1 && doc.status != 'Stopped' && roles.indexOf("Purchase Manager") != -1) {
            if (flt(doc.per_ordered, 2) < 100) {
                // make
                if (doc.material_request_type === "Material Transfer" && doc.status === "Submitted")
                    cur_frm.add_custom_button(__("Transfer Material"),
                        this.make_stock_entry, __("Make"));

                if (doc.material_request_type === "Material Issue" && doc.status === "Submitted")
                    cur_frm.add_custom_button(__("Issue Material"),
                        this.make_stock_entry, __("Make"));

                if (doc.material_request_type === "Purchase")
                    cur_frm.add_custom_button(__('Purchase Order'),
                        this.make_purchase_order, __("Make"));

                if (doc.material_request_type === "Purchase")
                    cur_frm.add_custom_button(__("Request for Quotation"),
                        this.make_request_for_quotation, __("Make"));

                if (doc.material_request_type === "Purchase")
                    cur_frm.add_custom_button(__("Supplier Quotation"),
                        this.make_supplier_quotation, __("Make"));

                if (doc.material_request_type === "Manufacture" && doc.status === "Submitted")
                    cur_frm.add_custom_button(__("Production Order"),
                        function() { me.raise_production_orders() }, __("Make"));

                cur_frm.page.set_inner_btn_group_as_primary(__("Make"));

                // stop
                cur_frm.add_custom_button(__('Stop'),
                    cur_frm.cscript['Stop Material Request']);

            }
        }

        if (this.frm.doc.docstatus === 0) {
            cur_frm.add_custom_button(__('Sales Order'),
                function() {
                    erpnext.utils.map_current_doc({
                        method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
                        source_doctype: "Sales Order",
                        get_query_filters: {
                            docstatus: 1,
                            status: ["!=", "Closed"],
                            per_delivered: ["<", 99.99],
                            company: cur_frm.doc.company
                        }
                    })
                }, __("Get items from"));
        }

        if (doc.docstatus == 1 && doc.status == 'Stopped')
            cur_frm.add_custom_button(__('Re-open'),
                cur_frm.cscript['Unstop Material Request']);

    },

    schedule_date: function(doc, cdt, cdn) {
        var val = locals[cdt][cdn].schedule_date;
        if (val) {
            $.each((doc.items || []), function(i, d) {
                if (!d.schedule_date) {
                    d.schedule_date = val;
                }
            });
            refresh_field("items");
        }
    },

    get_items_from_bom: function() {
        var d = new frappe.ui.Dialog({
            title: __("Get Items from BOM"),
            fields: [{
                    "fieldname": "bom",
                    "fieldtype": "Link",
                    "label": __("BOM"),
                    options: "BOM",
                    reqd: 1,
                    get_query: function() {
                        return { filters: { docstatus: 1 } }
                    }
                },
                {
                    "fieldname": "warehouse",
                    "fieldtype": "Link",
                    "label": __("Warehouse"),
                    options: "Warehouse",
                    reqd: 1,
                    label: "For Warehouse"
                },
                {
                    "fieldname": "fetch_exploded",
                    "fieldtype": "Check",
                    "label": __("Fetch exploded BOM (including sub-assemblies)"),
                    "default": 1
                },
                { fieldname: "fetch", "label": __("Get Items from BOM"), "fieldtype": "Button" }
            ]
        });
        d.get_input("fetch").on("click", function() {
            var values = d.get_values();
            if (!values) return;
            values["company"] = cur_frm.doc.company;
            frappe.call({
                method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
                args: values,
                callback: function(r) {
                    if (!r.message) {
                        frappe.throw(__("BOM does not contain any stock item"))
                    } else {
                        $.each(r.message, function(i, item) {
                            var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "items");
                            d.item_code = item.item_code;
                            d.description = item.description;
                            d.warehouse = values.warehouse;
                            d.uom = item.stock_uom;
                            d.qty = item.qty;
                        });
                    }
                    d.hide();
                    refresh_field("items");
                }
            });
        });
        d.show();
    },

    tc_name: function() {
        this.get_terms();
    },

    validate_company_and_party: function(party_field) {
        return true;
    },

    calculate_taxes_and_totals: function() {
        return;
    },

    make_purchase_order: function() {
        frappe.model.open_mapped_doc({
            method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
            frm: cur_frm,
            run_link_triggers: true
        });
    },

    make_request_for_quotation: function() {
        frappe.model.open_mapped_doc({
            method: "erpnext.stock.doctype.material_request.material_request.make_request_for_quotation",
            frm: cur_frm,
            run_link_triggers: true
        });
    },

    make_supplier_quotation: function() {
        frappe.model.open_mapped_doc({
            method: "erpnext.stock.doctype.material_request.material_request.make_supplier_quotation",
            frm: cur_frm
        });
    },

    make_stock_entry: function() {
        frappe.model.open_mapped_doc({
            method: "erpnext.stock.doctype.material_request.material_request.make_stock_entry",
            frm: cur_frm
        });
    },

    raise_production_orders: function() {
        var me = this;
        frappe.call({
            method: "erpnext.stock.doctype.material_request.material_request.raise_production_orders",
            args: {
                "material_request": me.frm.doc.name
            },
            callback: function(r) {
                if (r.message.length) {
                    me.frm.reload_doc();
                }
            }
        });
    }
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.MaterialRequestController({ frm: cur_frm }));

cur_frm.cscript['Stop Material Request'] = function() {
    var doc = cur_frm.doc;
    $c('runserverobj', args = { 'method': 'update_status', 'arg': 'Stopped', 'docs': doc }, function(r, rt) {
        cur_frm.refresh();
    });
};

cur_frm.cscript['Unstop Material Request'] = function() {
    var doc = cur_frm.doc;
    $c('runserverobj', args = { 'method': 'update_status', 'arg': 'Submitted', 'docs': doc }, function(r, rt) {
        cur_frm.refresh();
    });
};
cur_frm.cscript.custom_qty = cur_frm.cscript.custom_suggested_price_per_unit = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	frappe.model.set_value(d.doctype, d.name, "suggested_total_price", parseFloat(d.suggested_price_per_unit)*parseFloat(d.qty));
	var val = 0
    $.each((doc.items), function(i, d) {
        val += parseFloat(d.suggested_total_price);
    });
    cur_frm.set_value("suggested_grand_total", val);
}

// frappe.ui.form.on("Material Request", "validate", function (frm) {
//     if (user_roles.indexOf("Director") != -1 && frm.doc.workflow_state == "Pending") {
//         frappe.throw("Message to be printed");
//         frm.disable_save();
//     }
// });