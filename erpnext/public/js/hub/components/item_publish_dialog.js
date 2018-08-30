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

	hub.call('get_categories')
		.then(categories => {
			categories = categories.map(d => d.name);
			dialog.fields_dict.hub_category.set_data(categories);
		});

	return dialog;
}

export {
	ItemPublishDialog
}
