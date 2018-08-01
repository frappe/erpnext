import SubPage from './base_page';

erpnext.hub.Register = class Register extends SubPage {
	make_wrapper() {
		super.make_wrapper();
		this.$register_container = $(`<div class="row register-container">`)
			.appendTo(this.$wrapper);
		this.$form_container = $('<div class="col-md-8 col-md-offset-1 form-container">')
			.appendTo(this.$wrapper);
	}

	refresh() {
		this.$register_container.empty();
		this.$form_container.empty();
		this.render();
	}

	render() {
		this.make_field_group();
	}

	make_field_group() {
		const fields = [
			{
				fieldtype: 'Link',
				fieldname: 'company',
				label: __('Company'),
				options: 'Company',
				onchange: () => {
					const value = this.field_group.get_value('company');

					if (value) {
						frappe.db.get_doc('Company', value)
							.then(company => {
								this.field_group.set_values({
									country: company.country,
									company_email: company.email,
									currency: company.default_currency
								});
							});
					}
				}
			},
			{
				fieldname: 'company_email',
				label: __('Email'),
				fieldtype: 'Data'
			},
			{
				fieldname: 'country',
				label: __('Country'),
				fieldtype: 'Read Only'
			},
			{
				fieldname: 'currency',
				label: __('Currency'),
				fieldtype: 'Read Only'
			},
			{
				fieldtype: 'Text',
				label: __('About your Company'),
				fieldname: 'company_description'
			}
		];

		this.field_group = new frappe.ui.FieldGroup({
			parent: this.$form_container,
			fields
		});

		this.field_group.make();

		const default_company = frappe.defaults.get_default('company');
		this.field_group.set_value('company', default_company);

		this.$form_container.find('.form-column').append(`
			<div class="text-right">
				<button type="submit" class="btn btn-primary btn-register btn-sm">${__('Submit')}</button>
			</div>
		`);

		this.$form_container.find('.form-message').removeClass('hidden small').addClass('h4').text(__('Become a Seller'))

		this.$form_container.on('click', '.btn-register', (e) => {
			const form_values = this.field_group.get_values();

			let values_filled = true;
			const mandatory_fields = ['company', 'company_email', 'company_description'];
			mandatory_fields.forEach(field => {
				const value = form_values[field];
				if (!value) {
					this.field_group.set_df_property(field, 'reqd', 1);
					values_filled = false;
				}
			});
			if (!values_filled) return;

			frappe.call({
				method: 'erpnext.hub_node.doctype.hub_settings.hub_settings.register_seller',
				args: form_values,
				btn: $(e.currentTarget)
			}).then(() => {
				frappe.set_route('marketplace', 'publish');

				// custom jquery event
				this.$wrapper.trigger('seller-registered');
			});
		});
	}
}
