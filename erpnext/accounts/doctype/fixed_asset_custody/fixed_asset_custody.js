// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.fields_dict['fixed_asset'].get_query = function(doc) {
    return {
        filters: [
            ['status', 'not in', 'Scrapped, Sold'],
            ['status', 'in', 'Submitted']
        ]
    }
}

frappe.ui.form.on('Fixed Asset Custody', {
    refresh: function(frm) {
        if (frm.doc.docstatus == 1) {
            // if (frm.doc.status == 'Submitted' && !frm.doc.is_existing_asset && !frm.doc.purchase_invoice) {
            //     frm.add_custom_button("Make Purchase Invoice", function() {
            //         erpnext.asset.make_purchase_invoice(frm);
            //     });
            // }
            // if (in_list(["Submitted", "Partially Depreciated", "Fully Depreciated"], frm.doc.status)) {
            frm.add_custom_button(__("Transfer Asset"), function() {
                transfer_asset(frm);
            });

            frm.add_custom_button(__("Scrap Asset"), function() {
                scrap_asset(frm);
            });

            // }
        }
    }
});

scrap_asset = function(frm) {
    frappe.confirm(__("Do you really want to scrap this asset?"), function() {
        frappe.call({
            args: {
                "asset_name": frm.doc.fixed_asset
            },
            method: "erpnext.accounts.doctype.asset.depreciation.scrap_asset",
            callback: function(r) {
                cur_frm.reload_doc();
            }
        });
    });
}

transfer_asset = function(frm) {
    var dialog = new frappe.ui.Dialog({
        title: __("Transfer Asset"),
        fields: [{
            "label": __("Target Warehouse"),
            "fieldname": "target_warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "get_query": function() {
                return {
                    filters: [
                        ["Warehouse", "company", "in", ["", cstr(frm.doc.company)]],
                        ["Warehouse", "is_group", "=", 0]
                    ]
                }
            },
            "reqd": 1
        }, {
            "label": __("Date"),
            "fieldname": "transfer_date",
            "fieldtype": "Datetime",
            "reqd": 1,
            "default": frappe.datetime.now_datetime()
        }]
    });
    dialog.set_primary_action(__("Transfer"), function() {
        args = dialog.get_values();
        if (!args) return;
        dialog.hide();
        return frappe.call({
            type: "GET",
            method: "erpnext.accounts.doctype.asset.asset.transfer_asset",
            args: {
                args: {
                    "asset": frm.doc.fixed_asset,
                    "transaction_date": args.transfer_date,
                    // "source_warehouse": frm.doc.warehouse,
                    "target_warehouse": args.target_warehouse,
                    "company": frm.doc.company
                }
            },
            freeze: true,
            callback: function(r) {
                frappe.call({
                    method: "frappe.client.cancel",
                    args: {
                        doctype: cur_frm.doctype,
                        name: cur_frm.doc.name
                    },
                    callback: function(r) {
                        console.log(r);
                        cur_frm.reload_doc();
                    }
                });
            }
        })
    });
    dialog.show();
}
