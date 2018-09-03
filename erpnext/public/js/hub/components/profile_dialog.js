const ProfileDialog = (title = __('Edit Profile'), action={}) => {
	const fields = [
		{
			fieldname: 'company_email',
			label: __('Email'),
			fieldtype: 'Read Only'
		},
		{
			fieldtype: 'Link',
			fieldname: 'company',
			label: __('Company'),
			options: 'Company',
			onchange: () => {
				const value = dialog.get_value('company');
				if (value) {
					frappe.db.get_doc('Company', value)
						.then(company => {
							console.log(company.company_logo);
							dialog.set_values({
								company_logo: company.company_logo,
								company_description: company.company_description
							});
						});
				}
			}
		},
		// {
		// 	fieldname: 'company_logo',
		// 	label: __('Logo'),
		// 	fieldtype: 'Attach Image',
		// 	read_only: true
		// },
		{
			fieldname: 'company_description',
			label: __('About Your Company'),
			fieldtype: 'Long Text'
		}
	];

	let dialog = new frappe.ui.Dialog({
		title: title,
		fields: fields,
		primary_action_label: action.label || __('Update'),
		primary_action: () => {
			const form_values = dialog.get_values();
			let values_filled = true;

			// TODO: Say "we notice that the company description and logo isn't set. Please set them in master."
			// Only then allow to register

			const mandatory_fields = ['company'];
			mandatory_fields.forEach(field => {
				const value = form_values[field];
				if (!value) {
					dialog.set_df_property(field, 'reqd', 1);
					values_filled = false;
				}
			});
			if (!values_filled) return;

			action.on_submit(form_values);
		}
	});

	// Post create
	const default_company = frappe.defaults.get_default('company');
	dialog.set_value('company', default_company);
	dialog.set_value('company_email', frappe.session.user);

	return dialog;
}

export {
	ProfileDialog
}
