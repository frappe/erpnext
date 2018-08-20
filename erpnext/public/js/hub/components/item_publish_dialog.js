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
                "options": [],
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

    const hub_call_key = 'get_categories{}';

    erpnext.hub.on(`response:${hub_call_key}`, () => {
        dialog.fields_dict.hub_category.set_data(
            erpnext.hub.cache[hub_call_key].map(d => d.name)
        );
    });

    return dialog;
}

export {
    ItemPublishDialog
}
