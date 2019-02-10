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
						value: v
					}
				}),
				change: () => {
					this.on_attribute_selection();
				}
			}
		});

		this.dialog = new frappe.ui.Dialog({
			title: __('Configure {0}', [this.item_name]),
			fields,
			on_hide: () => {
				set_continue_configuration();
			}
		});

		this.attribute_data.forEach(a => {
			const field = this.dialog.get_field(a.attribute);
			const $a = $(`<a href>${__("Clear")}</a>`);
			$a.on('click', (e) => {
				e.preventDefault();
				this.dialog.set_value(a.attribute, '');
			});
			field.$wrapper.find('.help-box').append($a);
		});

		this.append_alert_box();
		this.dialog.show();

		this.dialog.set_values(JSON.parse(localStorage.getItem(this.get_cache_key())));

		$('.btn-configure').prop('disabled', false);
	}

	on_attribute_selection() {
		const values = this.dialog.get_values();
		if (Object.keys(values).length === 0) {
			this.dialog.$item_status.addClass('hidden').removeClass('d-flex');
			localStorage.removeItem(this.get_cache_key());
			return;
		}

		// save state
		localStorage.setItem(this.get_cache_key(), JSON.stringify(values));

		// show
		this.dialog.$item_status.addClass('d-flex').removeClass('hidden');
		this.dialog.$item_status.text(__('Loading...'));

		this.get_next_attribute_and_values(values)
			.then(data => {
				const {
					valid_options_for_attributes,
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
					this.dialog.get_field(attribute).set_options();
				}
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

	get_alert_message({ filtered_items_count, filtered_items, exact_match }) {
		const exact_match_message = __('1 exact match.');
		const one_item = exact_match.length === 1 ?
			exact_match[0] :
			filtered_items_count === 1 ?
			filtered_items[0] : '';

		const action_buttons = one_item ? `
			<div class="d-flex align-items-center">
			<a href class="btn-clear-values d-inline-block mr-3">
				${__('Clear values')}
			</a>
			<button class="btn btn-primary btn-add-to-cart" data-item-code="${one_item}">
				${__('Add to cart')}
			</button>
			</div>
		` : `
			<a href class="btn-clear-values">
				${__('Clear values')}
			</a>
		`;

		const items_found = filtered_items_count === 1 ?
			__('{0} item found.', [filtered_items_count]) :
			__('{0} items found.', [filtered_items_count]);

		return `
			<span>
				${exact_match.length === 1 ? '' : items_found}
				${exact_match.length === 1 ? `<span>${exact_match_message}</span>` : ''}
			</span>
			${action_buttons}
		`;
	}

	append_alert_box() {
		const $alert = $(`<div class="alert alert-warning d-flex justify-content-between align-items-center" role="alert"></div>`);
		$alert.on('click', '.btn-add-to-cart', (e) => {
			if (frappe.session.user !== 'Guest') {
				localStorage.removeItem(this.get_cache_key());
			}
			const item_code = $(e.currentTarget).data('item-code');
			erpnext.shopping_cart.update_cart({
				item_code,
				qty: 1
			});
			this.dialog.hide();
		});
		$alert.on('click', '.btn-clear-values', (e) => {
			e.preventDefault();
			this.dialog.clear();
			this.on_attribute_selection();
		})
		$alert.addClass('hidden').removeClass('d-flex');
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

	get_cache_key() {
		return `configure:${this.item_code}`;
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

function set_continue_configuration() {
	const $btn_configure = $('.btn-configure');
	const { itemCode } = $btn_configure.data();

	if (localStorage.getItem(`configure:${itemCode}`)) {
		$btn_configure.text(__('Continue Configuration'));
	} else {
		$btn_configure.text(__('Configure'));
	}
}

frappe.ready(() => {
	const $btn_configure = $('.btn-configure');
	const { itemCode, itemName } = $btn_configure.data();

	set_continue_configuration();

	$btn_configure.on('click', (e) => {
		$btn_configure.prop('disabled', true);
		new ItemConfigure(itemCode, itemName);
	});
});
