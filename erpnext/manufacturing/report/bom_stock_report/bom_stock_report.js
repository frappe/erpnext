frappe.query_reports["BOM Stock Report"] = {
    "filters": [
        {
            "fieldname":"bom",
            "label": __("BOM"),
            "fieldtype": "Link",
            "options": "BOM"
        },
    ]
}