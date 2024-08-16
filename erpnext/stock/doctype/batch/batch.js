// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Batch", {
	setup: (frm) => {
		frm.set_query("item", () => {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {
					is_stock_item: 1,
					has_batch_no: 1,
				},
			};
		});
	},
	refresh: (frm) => {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Ledger"), () => {
				frappe.route_options = {
					batch_no: frm.doc.name,
				};
				frappe.set_route("query-report", "Stock Ledger");
			});
			frm.trigger("make_dashboard");
		}
	},
	item: (frm) => {
		// frappe.db.get_value('Item', {name: frm.doc.item}, 'has_expiry_date', (r) => {
		// 	frm.toggle_reqd('expiry_date', r.has_expiry_date);
		// });
		frappe.db.get_value(
			"Item",
			{ name: frm.doc.item },
			["shelf_life_in_days", "has_expiry_date"],
			(r) => {
				if (r.has_expiry_date && r.shelf_life_in_days) {
					// Calculate expiry date based on shelf_life_in_days
					frm.set_value(
						"expiry_date",
						frappe.datetime.add_days(frm.doc.manufacturing_date, r.shelf_life_in_days)
					);
				} else if (r.has_expiry_date) {
					frm.toggle_reqd("expiry_date", r.has_expiry_date);
				}
			}
		);
	},
	make_dashboard: (frm) => {
		if (!frm.is_new()) {
			let for_stock_levels = 0;
			if (!frm.doc.batch_qty && frm.doc.expiry_date) {
				for_stock_levels = 1;
			}

			frappe.call({
				method: "erpnext.stock.doctype.batch.batch.get_batch_qty",
				args: { batch_no: frm.doc.name, item_code: frm.doc.item, for_stock_levels: for_stock_levels },
				callback: (r) => {
					if (!r.message) {
						return;
					}

					const section = frm.dashboard.add_section("", __("Stock Levels"));

					// sort by qty
					r.message.sort(function (a, b) {
						a.qty > b.qty ? 1 : -1;
					});

					const rows = $("<div></div>").appendTo(section);

					// show
					(r.message || []).forEach(function (d) {
						if (d.qty > 0) {
							$(`<div class='row' style='margin-bottom: 10px;'>
								<div class='col-sm-3 small' style='padding-top: 3px;'>${d.warehouse}</div>
								<div class='col-sm-3 small text-right' style='padding-top: 3px;'>${d.qty}</div>
								<div class='col-sm-6'>
									<button class='btn btn-default btn-xs btn-move' style='margin-right: 7px;'
										data-qty = "${d.qty}"
										data-warehouse = "${d.warehouse}">
										${__("Move")}</button>
									<button class='btn btn-default btn-xs btn-split'
										data-qty = "${d.qty}"
										data-warehouse = "${d.warehouse}">
										${__("Split")}</button>
								</div>
							</div>`).appendTo(rows);
						}
					});

					// move - ask for target warehouse and make stock entry
					rows.find(".btn-move").on("click", function () {
						const $btn = $(this);
						const fields = [
							{
								fieldname: "to_warehouse",
								label: __("To Warehouse"),
								fieldtype: "Link",
								options: "Warehouse",
							},
						];

						frappe.prompt(
							fields,
							(data) => {
								frappe.call({
									method: "erpnext.stock.doctype.stock_entry.stock_entry_utils.make_stock_entry",
									args: {
										item_code: frm.doc.item,
										batch_no: frm.doc.name,
										qty: $btn.attr("data-qty"),
										from_warehouse: $btn.attr("data-warehouse"),
										to_warehouse: data.to_warehouse,
										source_document: frm.doc.reference_name,
										reference_doctype: frm.doc.reference_doctype,
									},
									callback: (r) => {
										frappe.show_alert(
											__("Stock Entry {0} created", [
												'<a href="/app/stock-entry/' +
													r.message.name +
													'">' +
													r.message.name +
													"</a>",
											])
										);
										frm.refresh();
									},
								});
							},
							__("Select Target Warehouse"),
							__("Move")
						);
					});

					// split - ask for new qty and batch ID (optional)
					// and make stock entry via batch.batch_split
					rows.find(".btn-split").on("click", function () {
						const $btn = $(this);
						frappe.prompt(
							[
								{
									fieldname: "qty",
									label: __("New Batch Qty"),
									fieldtype: "Float",
									default: $btn.attr("data-qty"),
								},
								{
									fieldname: "new_batch_id",
									label: __("New Batch ID (Optional)"),
									fieldtype: "Data",
								},
							],
							(data) => {
								frappe
									.xcall("erpnext.stock.doctype.batch.batch.split_batch", {
										item_code: frm.doc.item,
										batch_no: frm.doc.name,
										qty: data.qty,
										warehouse: $btn.attr("data-warehouse"),
										new_batch_id: data.new_batch_id,
									})
									.then(() => frm.reload_doc());
							},
							__("Split Batch"),
							__("Split")
						);
					});

					frm.dashboard.show();
				},
			});
		}
	},
});

frappe.ui.form.on("Batch", "manufacturing_date", function (frm) {
	frappe.db.get_value("Item", { name: frm.doc.item }, ["shelf_life_in_days", "has_expiry_date"], (r) => {
		if (r.has_expiry_date && r.shelf_life_in_days) {
			// Calculate expiry date based on shelf_life_in_days
			frm.set_value(
				"expiry_date",
				frappe.datetime.add_days(frm.doc.manufacturing_date, r.shelf_life_in_days)
			);
		}
	});
});
