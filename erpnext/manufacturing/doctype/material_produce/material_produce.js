// // Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// // For license information, please see license.txt

// frappe.ui.form.on('Material Produce', {
// 	// refresh: function(frm) {

// 	// }
// });


// Copyright (c) 2021, Dexciss Technology and contributors
// For license information, please see license.txt

frappe.ui.form.on('Material Produce', {
    setup: function(frm){
        apply_filter(frm)
        frm.set_query('target_warehouse_address', function() {
			return {
				filters: {
					link_doctype: 'Warehouse',
					link_name: frm.doc.t_warehouse
				}
			}
		});
    },
    target_warehouse_address:function(frm){
        erpnext.utils.get_address_display(frm, 'target_warehouse_address', 'target_warehouse_display', false);
    },
//    refresh: function(frm){
//        if(frm.doc.docstatus == 1 && frm.doc.produced == 0)
//        {
//            frm.add_custom_button(__('Produce'),function() {
//                make_stock_entry(frm)
//            }).addClass('btn-primary');
//        }
//    },
	add_details: function(frm) {
	    frappe.call({
            doc: frm.doc,
            method: "set_produce_material",
            callback: function(r) {
                frm.clear_table('material_produce_details');
                frm.reload_doc();
            }
        });
	}
});

frappe.ui.form.on('Material Produce Item', {
    show_details: function(frm, cdt, cdn) {
        if (frm.doc.__islocal){
            frappe.throw(__("Please Save Material Produce first!"))
        }
        var row = locals[cdt][cdn];
        add_details_line(frm,row)
    },
});

function apply_filter(frm){
    frm.fields_dict['material_produce_details'].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
        let name = null
        for (var i =0; i < frm.doc.material_produce_details.length; i++)
	    {
	        if (frm.doc.material_produce_details[i].item_code){
	            name = frm.doc.material_produce_details[i].item_code
	            break;
	        }
	    }
        var child = locals[cdt][cdn];
        return {
            filters:[
               ['name', '=', name]
            ]
        }
    }
}


function make_stock_entry(frm){
    frappe.call({
        doc: frm.doc,
        method: "make_stock_entry",
        callback: function(r) {
            if (r.message) {
                var doc = frappe.model.sync(r.message)[0];
                frappe.set_route("Form", doc.doctype, doc.name);
            }
        }
    });
}

function add_details_line(frm,line_obj){
    console.log(frm.doc.amount);
    frappe.call({
        method: "add_details_line",
        doc: frm.doc,
        args: {
            line_id: line_obj.name,
            // company: frm.doc.company,
            item_code: line_obj.item_code,
            warehouse: line_obj.s_warehouse,
            qty_produced: line_obj.qty_produced,
            batch_size: frm.doc.batch_size,
            work_order: frm.doc.work_order,
            data:line_obj.data,
            amount: frm.doc.amount,
            type: line_obj.type,
            bom: frm.doc.bom,
            // cost_of_rm_consumed: frm.doc.cost_of_rm_consumed,
            // cost_of_operation_consumed: frm.doc.cost_of_operation_consumed,
            partial_produce: frm.doc.partial_produce
        },
        callback: function (r) {
            if(r.message){
                frm.refresh_field("cost_of_rm_consumed");
                frm.refresh_field("cost_of_operation_consumed");
                frm.clear_table('material_produce_details');
                for (const d of r.message){
                    var row = frm.add_child('material_produce_details');
                    row.item_code = d.item_code;
                    row.item_name= d.item_name,
                    row.t_warehouse = d.t_warehouse,
                    row.qty_produced = flt(d.qty_produced, precision('qty_produced', row)),
                    row.has_batch_no = d.has_batch_no,
                    row.batch_series = d.batch,
                    row.rate = flt(d.rate, precision('rate', row)),
                    row.weight = d.weight,
                    row.line_ref = d.line_ref
                    // row.work_order_total_cost=d.work_order_total_cost,
                    // row.scrap_total_cost=d.scrap_total_cost
                }
                frm.refresh_field('material_produce_details');
            }
            frm.save();
        }
    });
}
