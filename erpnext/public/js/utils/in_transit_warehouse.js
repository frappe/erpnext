frappe.provide('erpnext.utils');

erpnext.utils.prompt_in_transit_warehouse = (callback, company, title, primary_label) => {
	frappe.prompt(
		[
			{
				label: __('In Transit Warehouse'),
				fieldname: 'in_transit_warehouse',
				fieldtype: 'Link',
				options: 'Warehouse',
				reqd: 1,
				get_query: () => {
					return {
						filters: {
							'company': company,
							'is_group': 0,
							'warehouse_type': 'Transit'
						}
					}
				}
			}
		],
		(values) => {
			callback(values.in_transit_warehouse);
		},
		title,
		primary_label,
	);
};
