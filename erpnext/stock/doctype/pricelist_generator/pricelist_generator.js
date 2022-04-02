// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('PriceList Generator', {
    setup:function(frm){
        frm.set_query('cost_center', function(doc) {
			return {
				filters: {
					"is_group":0
				}
			};
		})
    },
	get_items: function(frm) {
        frm.clear_table("price_details")
        frm.refresh_field("price_details")
        const filters = frm.filters.reduce((acc, filter) => {
            return Object.assign(acc, {
                [filter[1]]: [filter[2], filter[3]]
            });
        }, {});
		frm.call({
            method:"get_items_brand",
            doc:frm.doc,
            freeze: true,
			freeze_message: __("Fetching Items..."),
            args:{
                filters:filters
            },
            callback: function(r) {
                if(r.message){
                        console.log("***",r.message);
						frm.refresh_field("price_details")
                    }
                }
        });
	},
    refresh: function(frm) {
		frm.set_df_property("filters_section", "hidden", 1);
		frm.trigger('set_options');
		frm.trigger('render_filters_table');

	},

	set_options: function(frm) {
		let aggregate_based_on_fields = [];
		const doctype = 'Item';

		if (doctype) {
			frappe.model.with_doctype(doctype, () => {
				frappe.get_meta(doctype).fields.map(df => {
					if (frappe.model.numeric_fieldtypes.includes(df.fieldtype)) {
						if (df.fieldtype == 'Currency') {
							if (!df.options || df.options !== 'Company:company:default_currency') {
								return;
							}
						}
						aggregate_based_on_fields.push({label: df.label, value: df.fieldname});
					}
				});

				frm.set_df_property('aggregate_function_based_on', 'options', aggregate_based_on_fields);
			});
		}
	},

	render_filters_table: function(frm) {
		frm.set_df_property("filters_section", "hidden", 0);

		let wrapper = $(frm.get_field('filters_json').wrapper).empty();
		frm.filter_table = $(`<table class="table table-bordered" style="cursor:pointer; margin:0px;">
			<thead>
				<tr>
					<th style="width: 33%">${__('Filter')}</th>
					<th style="width: 33%">${__('Condition')}</th>
					<th>${__('Value')}</th>
				</tr>
			</thead>
			<tbody></tbody>
		</table>`).appendTo(wrapper);

		frm.filters = JSON.parse(frm.doc.filters_json || '[]');

		frm.trigger('set_filters_in_table');

		frm.filter_table.on('click', () => {
			let dialog = new frappe.ui.Dialog({
				title: __('Set Filters'),
				fields: [{
					fieldtype: 'HTML',
					fieldname: 'filter_area',
				}],
				primary_action: function() {
					let values = this.get_values();
					if (values) {
						this.hide();
						frm.filters = frm.filter_group.get_filters();
						frm.set_value('filters_json', JSON.stringify(frm.filters));
						frm.trigger('set_filters_in_table');
					}
				},
				primary_action_label: "Set"
			});

			frappe.dashboards.filters_dialog = dialog;

			frm.filter_group = new frappe.ui.FilterGroup({
				parent: dialog.get_field('filter_area').$wrapper,
				doctype: 'Item',
				on_change: () => {},
			});

			frm.filter_group.add_filters_to_filter_group(frm.filters);

			dialog.show();
			dialog.set_values(frm.filters);
		});

	},

	set_filters_in_table: function(frm) {
		if (!frm.filters.length) {
			const filter_row = $(`<tr><td colspan="3" class="text-muted text-center">
				${__("Click to Set Filters")}</td></tr>`);
			frm.filter_table.find('tbody').html(filter_row);
		} else {
			let filter_rows = '';
			frm.filters.forEach(filter => {
				filter_rows +=
					`<tr>
						<td>${filter[1]}</td>
						<td>${filter[2] || ""}</td>
						<td>${filter[3]}</td>
					</tr>`;

			});
			frm.filter_table.find('tbody').html(filter_rows);
		}
	},




});

