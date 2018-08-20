function ItemPublishDialog(primary_action, secondary_action) {
    let dialog = new frappe.ui.Dialog({
        title: __('Edit Publishing Details'),
        fields: [
            {
                "label": "Item Code",
                "fieldname": "item_code",
                "fieldtype": "Data",
                "read_only": 1
            },
            {
                "label": "Hub Category",
                "fieldname": "hub_category",
                "fieldtype": "Autocomplete",
                "options": ["Agriculture", "Books", "Chemicals", "Clothing",
                    "Electrical", "Electronics", "Energy", "Fashion", "Food and Beverage",
                    "Health", "Home", "Industrial", "Machinery", "Packaging and Printing",
                    "Sports", "Transportation"
                ],
                "reqd": 1
            },
            {
                "label": "Images",
                "fieldname": "image_list",
                "fieldtype": "MultiSelect",
                "options": [],
                "reqd": 1
            }
        ],
        primary_action_label: primary_action.label || __('Set Details'),
        primary_action: primary_action.fn,
        secondary_action: secondary_action.fn
    });
    return dialog;
}

export {
    ItemPublishDialog
}
