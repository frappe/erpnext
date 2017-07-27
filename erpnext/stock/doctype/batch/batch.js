// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Batch', {
	setup: (frm) => {
		frm.fields_dict['item'].get_query = function(doc, cdt, cdn) {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters:{
					'is_stock_item': 1,
					'has_batch_no': 1
				}
			}
		}
	},
	refresh: (frm) => {
		if(!frm.is_new()) {
			frm.add_custom_button(__("View Ledger"), () => {
				frappe.route_options = {
					batch_no: frm.doc.name
				};
				frappe.set_route("query-report", "Stock Ledger");
			});
			frm.trigger('make_dashboard');
		}
	},
	make_dashboard: (frm) => {
		if(!frm.is_new()) {
			frappe.call({
				method: 'erpnext.stock.doctype.batch.batch.get_batch_qty',
				args: {batch_no: frm.doc.name},
				callback: (r) => {
					if(!r.message) {
						return;
					}

					var section = frm.dashboard.add_section(`<h5 style="margin-top: 0px;">
						${ __("Stock Levels") }</a></h5>`);

					// sort by qty
					r.message.sort(function(a, b) { a.qty > b.qty ? 1 : -1 });

					var rows = $('<div></div>').appendTo(section);

					// show
					(r.message || []).forEach(function(d) {
						if(d.qty > 0) {
							$(`<div class='row' style='margin-bottom: 10px;'>
								<div class='col-sm-3 small' style='padding-top: 3px;'>${d.warehouse}</div>
								<div class='col-sm-3 small text-right' style='padding-top: 3px;'>${d.qty}</div>
								<div class='col-sm-6'>
									<button class='btn btn-default btn-xs btn-move' style='margin-right: 7px;'
										data-qty = "${d.qty}"
										data-warehouse = "${d.warehouse}">
										${__('Move')}</button>
									<button class='btn btn-default btn-xs btn-split'
										data-qty = "${d.qty}"
										data-warehouse = "${d.warehouse}">
										${__('Split')}</button>
								</div>
							</div>`).appendTo(rows);
						}
					});

					// move - ask for target warehouse and make stock entry
					rows.find('.btn-move').on('click', function() {
						var $btn = $(this);
						frappe.prompt({
							fieldname: 'to_warehouse',
							label: __('To Warehouse'),
							fieldtype: 'Link',
							options: 'Warehouse'
						},
						(data) => {
							frappe.call({
								method: 'erpnext.stock.doctype.stock_entry.stock_entry_utils.make_stock_entry',
								args: {
									item_code: frm.doc.item,
									batch_no: frm.doc.name,
									qty: $btn.attr('data-qty'),
									from_warehouse: $btn.attr('data-warehouse'),
									to_warehouse: data.to_warehouse
								},
								callback: (r) => {
									frappe.show_alert(__('Stock Entry {0} created',
										['<a href="#Form/Stock Entry/'+r.message.name+'">' + r.message.name+ '</a>']));
									frm.refresh();
								},
							});
						},
						__('Select Target Warehouse'),
						__('Move')
						);
					});

					// split - ask for new qty and batch ID (optional)
					// and make stock entry via batch.batch_split
					rows.find('.btn-split').on('click', function() {
						var $btn = $(this);
						frappe.prompt([{
							fieldname: 'qty',
							label: __('New Batch Qty'),
							fieldtype: 'Float',
							'default': $btn.attr('data-qty')
						},
						{
							fieldname: 'new_batch_id',
							label: __('New Batch ID (Optional)'),
							fieldtype: 'Data',
						}],
						(data) => {
							frappe.call({
								method: 'erpnext.stock.doctype.batch.batch.split_batch',
								args: {
									item_code: frm.doc.item,
									batch_no: frm.doc.name,
									qty: data.qty,
									warehouse: $btn.attr('data-warehouse'),
									new_batch_id: data.new_batch_id
								},
								callback: (r) => {
									frm.refresh();
								},
							});
						},
						__('Split Batch'),
						__('Split')
						);
					})

					frm.dashboard.show();
				}
			});
		}
	}
})

