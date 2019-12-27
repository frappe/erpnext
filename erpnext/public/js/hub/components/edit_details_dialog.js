function edit_details_dialog(params) {
	let dialog = new frappe.ui.Dialog({
		title: __('Update Details'),
		fields: [
			{
				label: 'Item Name',
				fieldname: 'item_name',
				fieldtype: 'Data',
				default: params.defaults.item_name,
				reqd: 1
			},
			{
				label: 'Hub Category',
				fieldname: 'hub_category',
				fieldtype: 'Autocomplete',
				default: params.defaults.hub_category,
				options: [],
				reqd: 1
			},
			{
				label: 'Description',
				fieldname: 'description',
				fieldtype: 'Text',
				default: params.defaults.description,
				options: [],
				reqd: 1
			}
		],
		primary_action_label: params.primary_action.label || __('Update Details'),
		primary_action: params.primary_action.fn
	});

	hub.call('get_categories').then(categories => {
		categories = categories.map(d => d.name);
		dialog.fields_dict.hub_category.set_data(categories);
	});

	return dialog;
}

export { edit_details_dialog };
