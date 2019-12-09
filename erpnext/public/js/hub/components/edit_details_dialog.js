function EditDetailsDialog(primary_action, defaults) {
	let dialog = new frappe.ui.Dialog({
		title: __('Update Details'),
		fields: [
			{
				label: 'Item Name',
				fieldname: 'item_name',
				fieldtype: 'Data',
				default: defaults.item_name,
				reqd: 1
			},
			{
				label: 'Hub Category',
				fieldname: 'hub_category',
				fieldtype: 'Autocomplete',
				default: defaults.hub_category,
				options: [],
				reqd: 1
			},
			{
				label: 'Description',
				fieldname: 'description',
				fieldtype: 'Text',
				default: defaults.description,
				options: [],
				reqd: 1
			}
		],
		primary_action_label: primary_action.label || __('Update Details'),
		primary_action: primary_action.fn
	});

	hub.call('get_categories').then(categories => {
		categories = categories.map(d => d.name);
		dialog.fields_dict.hub_category.set_data(categories);
	});

	return dialog;
}

export { EditDetailsDialog };
