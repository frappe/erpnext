frappe.provide("frappe.treeview_settings");

frappe.treeview_settings['Healthcare Service Unit'] = {
	breadcrumbs: 'Healthcare Service Unit',
	title: __('Service Unit Tree'),
	get_tree_root: false,
	get_tree_nodes: 'erpnext.healthcare.utils.get_children',
	filters: [{
		fieldname: 'company',
		fieldtype: 'Select',
		options: erpnext.utils.get_tree_options('company'),
		label: __('Company'),
		default: erpnext.utils.get_tree_default('company')
	}],
	fields: [
		{
			fieldtype: 'Data', fieldname: 'healthcare_service_unit_name', label: __('New Service Unit Name'),
			reqd: true
		},
		{
			fieldtype: 'Check', fieldname: 'is_group', label: __('Is Group'),
			description: __("Child nodes can be only created under 'Group' type nodes")
		},
		{
			fieldtype: 'Link', fieldname: 'service_unit_type', label: __('Service Unit Type'),
			options: 'Healthcare Service Unit Type', description: __('Type of the new Service Unit'),
			depends_on: 'eval:!doc.is_group', default: '',
			onchange: () => {
				if (cur_dialog) {
					if (cur_dialog.fields_dict.service_unit_type.value) {
						frappe.db.get_value('Healthcare Service Unit Type',
							cur_dialog.fields_dict.service_unit_type.value, 'overlap_appointments')
							.then(r => {
								if (r.message.overlap_appointments) {
									cur_dialog.set_df_property('service_unit_capacity', 'hidden', false);
									cur_dialog.set_df_property('service_unit_capacity', 'reqd', true);
								} else {
									cur_dialog.set_df_property('service_unit_capacity', 'hidden', true);
									cur_dialog.set_df_property('service_unit_capacity', 'reqd', false);
								}
							});
					} else {
						cur_dialog.set_df_property('service_unit_capacity', 'hidden', true);
						cur_dialog.set_df_property('service_unit_capacity', 'reqd', false);
					}
				}
			}
		},
		{
			fieldtype: 'Int', fieldname: 'service_unit_capacity', label: __('Service Unit Capacity'),
			description: __('Sets the number of concurrent appointments allowed'), reqd: false,
			depends_on: "eval:!doc.is_group && doc.service_unit_type != ''", hidden: true
		},
		{
			fieldtype: 'Link', fieldname: 'warehouse', label: __('Warehouse'), options: 'Warehouse',
			description: __('Optional, if you want to manage stock separately for this Service Unit'),
			depends_on: 'eval:!doc.is_group'
		},
		{
			fieldtype: 'Link', fieldname: 'company', label: __('Company'), options: 'Company', reqd: true,
			default: () => {
				return cur_page.page.page.fields_dict.company.value;
			}
		}
	],
	ignore_fields: ['parent_healthcare_service_unit'],
	onrender: function (node) {
		if (node.data.occupied_of_available !== undefined) {
			$("<span class='balance-area pull-right text-muted small'>"
				+ ' ' + node.data.occupied_of_available
				+ '</span>').insertBefore(node.$ul);
		}
		if (node.data && node.data.inpatient_occupancy !== undefined) {
			if (node.data.inpatient_occupancy == 1) {
				if (node.data.occupancy_status == 'Occupied') {
					$("<span class='balance-area pull-right small'>"
						+ ' ' + node.data.occupancy_status
						+ '</span>').insertBefore(node.$ul);
				}
				if (node.data.occupancy_status == 'Vacant') {
					$("<span class='balance-area pull-right text-muted small'>"
						+ ' ' + node.data.occupancy_status
						+ '</span>').insertBefore(node.$ul);
				}
			}
		}
	},
	post_render: function (treeview) {
		frappe.treeview_settings['Healthcare Service Unit'].treeview = {};
		$.extend(frappe.treeview_settings['Healthcare Service Unit'].treeview, treeview);
	},
	toolbar: [
		{
			label: __('Add Multiple'),
			condition: function (node) {
				return node.expandable;
			},
			click: function (node) {
				const dialog = new frappe.ui.Dialog({
					title: __('Add Multiple Service Units'),
					fields: [
						{
							fieldtype: 'Data', fieldname: 'healthcare_service_unit_name', label: __('Service Unit Name'),
							reqd: true, description: __("Will be serially suffixed to maintain uniquness. Example: 'Ward' will be named as 'Ward-####'"),
						},
						{
							fieldtype: 'Int', fieldname: 'count', label: __('Number of Service Units'),
							reqd: true
						},
						{
							fieldtype: 'Link', fieldname: 'service_unit_type', label: __('Service Unit Type'),
							options: 'Healthcare Service Unit Type', description: __('Type of the new Service Unit'),
							depends_on: 'eval:!doc.is_group', default: '', reqd: true,
							onchange: () => {
								if (cur_dialog) {
									if (cur_dialog.fields_dict.service_unit_type.value) {
										frappe.db.get_value('Healthcare Service Unit Type',
											cur_dialog.fields_dict.service_unit_type.value, 'overlap_appointments')
											.then(r => {
												if (r.message.overlap_appointments) {
													cur_dialog.set_df_property('service_unit_capacity', 'hidden', false);
													cur_dialog.set_df_property('service_unit_capacity', 'reqd', true);
												} else {
													cur_dialog.set_df_property('service_unit_capacity', 'hidden', true);
													cur_dialog.set_df_property('service_unit_capacity', 'reqd', false);
												}
											});
									} else {
										cur_dialog.set_df_property('service_unit_capacity', 'hidden', true);
										cur_dialog.set_df_property('service_unit_capacity', 'reqd', false);
									}
								}
							}
						},
						{
							fieldtype: 'Int', fieldname: 'service_unit_capacity', label: __('Service Unit Capacity'),
							description: __('Sets the number of concurrent appointments allowed'), reqd: false,
							depends_on: "eval:!doc.is_group && doc.service_unit_type != ''", hidden: true
						},
						{
							fieldtype: 'Link', fieldname: 'warehouse', label: __('Warehouse'), options: 'Warehouse',
							description: __('Optional, if you want to manage stock separately for this Service Unit'),
						},
						{
							fieldtype: 'Link', fieldname: 'company', label: __('Company'), options: 'Company', reqd: true,
							default: () => {
								return cur_page.page.page.fields_dict.company.get_value();
							}
						}
					],
					primary_action: () => {
						dialog.hide();
						let vals = dialog.get_values();
						if (!vals) return;

						return frappe.call({
							method: 'erpnext.healthcare.doctype.healthcare_service_unit.healthcare_service_unit.add_multiple_service_units',
							args: {
								parent: node.data.value,
								data: vals
							},
							callback: function (r) {
								if (!r.exc && r.message) {
									frappe.treeview_settings['Healthcare Service Unit'].treeview.tree.load_children(node, true);

									frappe.show_alert({
										message: __('{0} Service Units created', [vals.count - r.message.length]),
										indicator: 'green'
									});
								} else {
									frappe.msgprint(__('Could not create Service Units'));
								}
							},
							freeze: true,
							freeze_message: __('Creating {0} Service Units', [vals.count])
						});
					},
					primary_action_label: __('Create')
				});
				dialog.show();
			}
		}
	],
	extend_toolbar: true
};
