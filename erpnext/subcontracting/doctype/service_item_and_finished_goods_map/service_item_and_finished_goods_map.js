// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Item and Finished Goods Map", {
	setup: (frm) => {
		frm.trigger("set_queries");
	},

    set_queries: (frm) => {
        frm.set_query("service_item", () => {
            return {
                filters: {
                    disabled: 0,
                    is_stock_item: 0,
                }
            }
        });

        frm.set_query("finished_good_item", "finished_goods_detail", () => {
            var selected_fg_items = frm.doc.finished_goods_detail.map(row => {
				return row.finished_good_item;
			});

            return {
                filters: {
                    disabled: 0,
                    is_stock_item: 1,
                    default_bom: ['!=', ''],
                    is_sub_contracted_item: 1,
                    item_code: ["not in", selected_fg_items],
                }
            }
        });

        frm.set_query("bom", "finished_goods_detail", (doc, cdt, cdn) => {
            var row = locals[cdt][cdn];

            return {
                filters: {
                    docstatus: 1,
                    is_active: 1,
                    item: row.finished_good_item,
                }
            }
        });
    }
});
