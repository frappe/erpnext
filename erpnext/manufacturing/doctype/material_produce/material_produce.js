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
    frappe.call({
        method: "erpnext.manufacturing.doctype.material_produce.material_produce.add_details_line",
        args: {
            line_id: line_obj.name,
            company: frm.doc.company,
            item_code: line_obj.item_code,
            warehouse: line_obj.s_warehouse,
            qty_produced: line_obj.qty_produced,
            batch_size: frm.doc.batch_size,
            work_order: frm.doc.work_order,
            data:line_obj.data,
            amount: frm.doc.amount
        },
        callback: function (r) {
            if(r.message){
                frm.clear_table('material_produce_details');
                for (const d of r.message){
                    var row = frm.add_child('material_produce_details');
                    row.item_code = d.item_code;
                    row.item_name= d.item_name,
                    row.t_warehouse = d.t_warehouse,
                    row.qty_produced = d.qty_produced,
                    row.has_batch_no = d.has_batch_no,
                    row.batch = d.batch,
                    row.rate = d.rate,
                    row.weight = d.weight,
                    row.line_ref = d.line_ref
                }
                frm.refresh_field('material_produce_details');
            }
        }
    });
}
