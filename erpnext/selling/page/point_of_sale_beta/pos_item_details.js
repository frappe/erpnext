erpnext.PointOfSale.ItemDetails = class {
    constructor({ wrapper, events }) {
		this.wrapper = wrapper;
        this.events = events;
        this.current_item = {};

        this.intialize_component();
    }

    intialize_component() {
        this.prepare_dom();
        this.initialize_child_components();
        this.bind_events();
    }

    prepare_dom() {
        this.wrapper.append(
            `<section class="col-span-4 flex shadow rounded item-details bg-white mx-h-70 h-100 d-none"></section>`
        )

        this.$component = this.wrapper.find('.item-details');
    }

    initialize_child_components() {
		this.$component.html(
			`<div class="details-container flex flex-col p-8 rounded w-full">
				<div class="item-defaults flex">
					<div class="flex-1 flex flex-col justify-end mr-4 mb-2">
						<div class="text-grey mb-auto">ITEM DETAILS</div>
						<div class="item-name text-xl font-weight-450"></div>
						<div class="item-description text-md-0 text-grey-200"></div>
						<div class="item-price text-xl font-bold"></div>
					</div>
					<div class="item-image flex items-center justify-center w-46 h-46 bg-light-grey rounded ml-4 text-6xl text-grey-100"></div>
				</div>
				<div class="discount-section flex items-center"></div>
				<div class="text-grey mt-4 mb-6">STOCK DETAILS</div>
				<div class="form-container grid grid-cols-2 row-gap-2 col-gap-4 grid-auto-row"></div>
			</div>`
		)

		this.$item_name = this.$component.find('.item-name');
		this.$item_description = this.$component.find('.item-description');
		this.$item_price = this.$component.find('.item-price');
		this.$item_image = this.$component.find('.item-image');
		this.$form_container = this.$component.find('.form-container');
		this.$dicount_section = this.$component.find('.discount-section');
    }

    toggle_item_details_section(item) {
        const { item_code, batch_no } = this.current_item; // to check if already displaying and item
        this.show_details = !item ? false : item_code === item.item_code && batch_no === item.batch_no ? false : true;

        this.events.toggle_item_selector(this.show_details);
        this.show_details ?
            this.$component.removeClass('d-none') :
            this.$component.addClass('d-none');
        
		if (this.show_details) {
            this.doctype = item.doctype;
			this.item_meta = frappe.get_meta(this.doctype);
            this.name = item.name;
            this.currency = this.events.get_frm().doc.currency;
            
            this.current_item = { item_code: item.item_code, batch_no: item.batch_no };
            
			this.render_dom(item);
			this.render_discount_dom(item);
			this.render_form(item);
		} else {
			this.current_item = {};
		}
    }
    
    render_dom(item) {
        let { item_code ,item_name, description, image, price_list_rate } = item;

		function get_description_html() {
			if (description) {
				description = description.indexOf('...') === -1 && description.length > 75 ? description.substr(0, 73) + '...' : description;
				return description;
			}
			return ``;
        }
        
		this.$item_name.html(item_name);
		this.$item_description.html(get_description_html());
		this.$item_price.html(format_currency(price_list_rate, this.currency));
		if (image) {
			this.$item_image.html(
				`<img class="h-full" src="${image}" alt="${image}" style="object-fit: cover;">`
			);
		} else {
			this.$item_image.html(frappe.get_abbr(item_code));
		}

    }
    
    render_discount_dom(item) {
		if (item.discount_percentage) {
			this.$dicount_section.html(
				`<div class="text-grey line-through mr-4 text-md mb-2">
					${format_currency(item.price_list_rate, this.currency)}
				</div>
				<div class="p-1 pr-3 pl-3 rounded w-fit text-bold bg-green-200 mb-2">
					${item.discount_percentage}% off
				</div>`
			)
			this.$item_price.html(format_currency(item.rate, this.currency));
		} else {
			this.$dicount_section.html(``)
		}
    }

    render_form(item) {
		const fields_to_display = this.get_form_fields(item);
		this.$form_container.html('');

		fields_to_display.forEach((fieldname, idx) => {
			this.$form_container.append(
				`<div class="">
					<div class="item_detail_field ${fieldname}-control" data-fieldname="${fieldname}"></div>
				</div>`
			)

			const field_meta = this.item_meta.fields.find(df => df.fieldname === fieldname);
			fieldname === 'discount_percentage' ? (field_meta.label = __('Discount (%)')) : '';
			const me = this;
            
			this[`${fieldname}_control`] = frappe.ui.form.make_control({
				df: { 
					...field_meta, 
					onchange: function() {
						me.events.form_updated(me.doctype, me.name, fieldname, this.value);
					}
				},
				parent: this.$form_container.find(`.${fieldname}-control`),
				render_input: true,
			})
			this[`${fieldname}_control`].set_value(item[fieldname]);
		})

		this.make_auto_serial_selection_btn(item);

		this.bind_custom_control_change_event();
    }

    get_form_fields(item) {
		const fields = ['qty', 'rate', 'discount_percentage', 'price_list_rate', 'warehouse', 'actual_qty'];
		if (item.has_serial_no) fields.push('serial_no');
		if (item.has_batch_no) fields.push('batch_no');
		return fields;
	}

    make_auto_serial_selection_btn(item) {
		if (item.has_serial_no) {
			this.$form_container.append(
				`<div class="grid-filler no-select"></div>`
			)
			this.$form_container.append(
				`<div class="auto-fetch-btn bg-grey-100 border border-grey text-bold rounded pt-3 pb-3 pl-6 pr-8 text-grey pointer no-select mt-2"
						style="height: 3.3rem">
					Auto Fetch Serial Numbers
				</div>`
			)
			this.$form_container.find('.serial_no-control').find('textarea').css('height', '9rem');
			this.$form_container.find('.serial_no-control').parent().addClass('row-span-2');
		}
	}
    
    bind_custom_control_change_event() {
		const me = this;
		if (this.rate_control) {
			this.rate_control.df.onchange = function() {
				if (this.value) {
					me.events.form_updated(me.doctype, me.name, 'rate', this.value).then(() => {
						const item_row = frappe.get_doc(me.doctype, me.name);
						const doc = me.events.get_frm().doc;

						me.$item_price.html(format_currency(item_row.rate, doc.currency));
						me.render_discount_dom(item_row);
					});
				}
			}
		}

		if (this.discount_percentage_control) {
			this.discount_percentage_control.df.onchange = function() {
				if (this.value) {
					me.events.form_updated(me.doctype, me.name, 'discount_percentage', this.value).then(() => {
						const item_row = frappe.get_doc(me.doctype, me.name);
						me.rate_control.set_value(item_row.rate);
					});
				}
			}
		}

		if (this.serial_no_control) {
			this.serial_no_control.df.reqd = 1;
			this.serial_no_control.df.onchange = async function() {
				!me.current_item.batch_no && await me.auto_update_batch_no();
				me.events.form_updated(me.doctype, me.name, 'serial_no', this.value);
			}
		}

		if (this.batch_no_control) {
			this.batch_no_control.df.reqd = 1;
			this.batch_no_control.df.onchange = function() {
				me.events.set_batch_in_current_cart_item(this.value);
                me.events.form_updated(me.doctype, me.name, 'batch_no', this.value);
                me.current_item.batch_no = this.value;
			}
		}

		frappe.ui.form.on('POS Invoice Item', 'rate', (frm, cdt, cdn) => {
		})
    }
    
    async auto_update_batch_no() {
		if (this.serial_no_control && this.batch_no_control) {
			// find batch nos of the selected serial no 
			const selected_serial_nos = this.serial_no_control.get_value().split(`\n`).filter(s => s);

			if (!selected_serial_nos.length) return;

			const response = await frappe.db.get_list("Serial No", {
				filters: { 'name': ["in", selected_serial_nos]},
				fields: ["batch_no", "name"]
			});
			const batch_serial_map = response.reduce((acc, r) => {
				acc[r.batch_no] || (acc[r.batch_no] = []);
				acc[r.batch_no] = [...acc[r.batch_no], r.name];
				return acc;
			}, {});
			// set current item's batch no and serial no
			const batch_no = Object.keys(batch_serial_map)[0];
			const batch_serial_nos = batch_serial_map[batch_no].join(`\n`);
			// eg. 10 selected serial no. 5 belongs to first batch other 5 belongs to second batch
            const serial_nos_belongs_to_other_batch = selected_serial_nos.length !== batch_serial_map[batch_no].length;
            
            const current_batch_no = this.batch_no_control.get_value();
			current_batch_no != batch_no && await this.batch_no_control.set_value(batch_no);

			if (serial_nos_belongs_to_other_batch) {
				this.serial_no_control.set_value(batch_serial_nos);
				this.qty_control.set_value(batch_serial_map[batch_no].length);
			}

			delete batch_serial_map[batch_no];

			if (serial_nos_belongs_to_other_batch)
				this.events.clone_new_batch_item_in_frm(batch_serial_map, this.current_item);
		}
	}
    
    bind_events() {
		this.bind_auto_serial_fetch_event();
		this.bind_fields_to_numpad_fields();
    }

    bind_fields_to_numpad_fields() {
		const me = this;
		this.$form_container.on('click', '.input-with-feedback', function() {
			const fieldname = $(this).attr('data-fieldname');
			me.events.item_field_focused(fieldname);
		});
		// this.$form_container.on('focusout', '.input-with-feedback', function() {
		// 	const fieldname = $(this).attr('data-fieldname');
		// 	me.events.item_field_focused(fieldname);
		// });
	}
    
    bind_auto_serial_fetch_event() {
		this.$form_container.on('click', '.auto-fetch-btn', () => {
			this.batch_no_control.set_value('');
			let qty = this.qty_control.get_value();
			let numbers = frappe.call({
				method: "erpnext.stock.doctype.serial_no.serial_no.auto_fetch_serial_number",
				args: {
					qty,
					item_code: this.current_item.item_code,
					warehouse: this.warehouse_control.get_value() || '',
					batch_nos: this.current_item.batch_no || '',
					for_doctype: 'POS Invoice'
				}
			});

			numbers.then((data) => {
				let auto_fetched_serial_numbers = data.message;
				let records_length = auto_fetched_serial_numbers.length;
				if (!records_length) {
					const warehouse = this.warehouse_control.get_value().bold();
					frappe.msgprint(__(`Serial numbers unavailable for Item ${this.current_item.item_code.bold()} 
						under warehouse ${warehouse}. Please try changing warehouse.`));
				} else if (records_length < qty) {
					frappe.msgprint(`Fetched only ${records_length} available serial numbers.`);
					this.qty_control.set_value(records_length);
				}
                numbers = auto_fetched_serial_numbers.join(`\n`);
				this.serial_no_control.set_value(numbers);
			});
		})
	}

	disable_item_details() {
        this.$component.addClass('d-none');
    }	
    
}