const ProfileDialog = (title = __('Edit Profile'), action={}) => {
	const fields = [
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
							dialog.set_values({
								country: company.country,
								currency: company.default_currency
							});
						});
				}
			}
		},
		{
			fieldname: 'company_email',
			label: __('Email'),
			fieldtype: 'Read Only'
		},
		{
			fieldtype: 'Text',
			label: __('About your Company'),
			fieldname: 'company_description'
		}
	];

	let dialog = new frappe.ui.Dialog({
		title: title,
		fields: fields,
		primary_action_label: action.label || __('Update'),
		primary_action: () => {
			const form_values = dialog.get_values();
			let values_filled = true;
			const mandatory_fields = ['company', 'company_email', 'company_description'];
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
