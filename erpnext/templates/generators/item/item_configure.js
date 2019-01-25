class ItemConfigure {
	constructor(item_code, item_name) {
		this.item_code = item_code;
		this.item_name = item_name;

		this.get_attributes_and_values()
			.then(attribute_data => {
				this.attribute_data = attribute_data;
				this.show_configure_dialog();
			});
	}

	show_configure_dialog() {
		const fields = this.attribute_data.map(a => {
			return {
				fieldtype: 'Select',
				label: a.attribute,
				fieldname: a.attribute,
				options: a.values.map(v => {
					return {
						label: v,
						value: v,
						disabled: !a.valid_values.includes(v)
					}
				}),
				change: () => {
					this.on_attribute_selection();
				}
			}
		});

		this.dialog = new frappe.ui.Dialog({
			title: __('Configure {0}', [this.item_name]),
			fields
		});

		fields.forEach((df, i) => {
			if (i !== 0) {
				this.dialog.get_field(df.fieldname).$wrapper.hide();
			}
		});

		this.append_alert_box();
		this.dialog.show();
		$('.btn-configure').prop('disabled', false);
	}

	on_attribute_selection() {
		const values = this.dialog.get_values();

		this.dialog.$item_status.show();
		this.dialog.$item_status.text(__('Loading...'));

		this.get_next_attribute_and_values(values)
			.then(data => {
				console.log(data)

				const {
					next_attribute,
					valid_options_for_attributes,
					filtered_items_count,
					filtered_items,
					exact_match
				} = data;

				this.dialog.$item_status.html(this.get_alert_message(data));

				for (let attribute in valid_options_for_attributes) {
					const valid_options = valid_options_for_attributes[attribute];
					const options = this.dialog.get_field(attribute).df.options;
					const new_options = options.map(o => {
						o.disabled = !valid_options.includes(o.value);
						return o;
					});
					this.dialog.set_df_property(attribute, 'options', new_options);
				}

				if (next_attribute) {
					this.dialog.get_field(next_attribute).$wrapper.show();
				}

				this.show_remaining_optional_attributes();
			});
	}

	show_remaining_optional_attributes() {
		// show all attributes if remaining
		// unselected attributes are all optional
		const unselected_attributes = this.dialog.fields.filter(df => {
			const value_selected = this.dialog.get_value(df.fieldname);
			return !value_selected;
		});
		const is_optional_attribute = df => {
			const optional_attributes = this.attribute_data
				.filter(a => a.optional).map(a => a.attribute);
			return optional_attributes.includes(df.fieldname);
		};
		if (unselected_attributes.every(is_optional_attribute)) {
			unselected_attributes.forEach(df => {
				this.dialog.fields_dict[df.fieldname].$wrapper.show();
			});
		}
	}

	get_alert_message({ filtered_items_count, exact_match }) {
		const exact_match_message = __('1 exact match.');
		const one_item = exact_match.length === 1 ?
			exact_match[0] :
			filtered_items_count === 1 ?
			filtered_items[0] : '';

		const add_to_cart = one_item ? `
			<button class="btn btn-primary btn-add-to-cart" data-item-code="${one_item}">
				${__('Add to cart')}
			</button>
		` : '';

		const items_found = filtered_items_count === 1 ?
			__('{0} items found.', [filtered_items_count]) :
			__('{0} item found.', [filtered_items_count]);

		return `
			<span>
				${items_found}
				${exact_match.length === 1 ? `<span>${exact_match_message}</span>` : ''}
			</span>
			${add_to_cart}
		`;
	}

	append_alert_box() {
		const $alert = $(`<div class="alert alert-warning d-flex justify-content-between align-items-center" role="alert"></div>`);
		$alert.on('click', '.btn-add-to-cart', (e) => {
			const item_code = $(e.currentTarget).data('item-code');
			erpnext.shopping_cart.update_cart({
				item_code,
				qty: 1
			});
			this.dialog.hide();
		});
		$alert.hide();
		this.dialog.$item_status = $alert;
		this.dialog.$wrapper.find('.modal-body').prepend($alert);
		this.dialog.$body.css({ maxHeight: '75vh', overflow: 'auto', overflowX: 'hidden' });
	}

	get_next_attribute_and_values(selected_attributes) {
		return this.call('erpnext.www.products.index.get_next_attribute_and_values', {
			item_code: this.item_code,
			selected_attributes
		});
	}

	get_attributes_and_values() {
		return this.call('erpnext.www.products.index.get_attributes_and_values', {
			item_code: this.item_code
		});
	}

	call(method, args) {
		// promisified frappe.call
		return new Promise((resolve, reject) => {
			frappe.call(method, args)
				.then(r => resolve(r.message))
				.fail(reject);
		});
	}
}

frappe.ready(() => {
	$('.btn-configure').on('click', (e) => {
		const $btn = $(e.target);
		$btn.prop('disabled', true);
		const { itemCode, itemName } = $(e.target).data();
		new ItemConfigure(itemCode, itemName);
	});
});
