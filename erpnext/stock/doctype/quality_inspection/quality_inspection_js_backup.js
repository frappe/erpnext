// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

// item code based on GRN/DN
cur_frm.fields_dict['item_code'].get_query = function(doc, cdt, cdn) {
	if (doc.reference_type && doc.reference_name) {
		return {
			query: "erpnext.stock.doctype.quality_inspection.quality_inspection.item_query",
			filters: {
				"from": doc.reference_type + " Item",
				"parent": doc.reference_name
			}
		}
	}
}

// Serial No based on item_code
cur_frm.fields_dict['item_serial_no'].get_query = function(doc, cdt, cdn) {
	var filters = {};
	if (doc.item_code) {
		filters = {
			'item_code': doc.item_code
		}
	}
	return { filters: filters }
}

frappe.ui.form.on("Quality Inspection", "item_group", function(frm) {

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Item Group Quality Checks",
            filters: {"parent":"Laptops"},    //user is current user here
            fields: ["name","`check`"]
        },
        callback: function(r) {
            $.each(r.message, function(idx,val){
                var new_row = cur_frm.add_child("readings")
                frappe.model.set_value(new_row.doctype, new_row.name)
                cur_frm.refresh_field("readings");
                var grid_row = cur_frm.fields_dict['readings'].grid.grid_rows_by_docname[new_row.name],
                field = frappe.utils.filter_dict(grid_row.docfields, {fieldname: "qc_options"})[0];
//                console.log("here")
                grid_row.grid.grid_rows[idx].doc.quality_check_item = val.check
                grid_row.grid.grid_rows[idx].refresh_field("quality_check_item")

//                var row_field = grid_row.grid.grid_rows[idx].columns_list[1].df;
                var row_field = grid_row.columns_list[1].df;
                row_field.get_query =  function(){
                    return {
            //            query: "erpnext.stock.doctype.quality_inspection.quality_inspection.quality_check_options",
                        filters: { parent: val.check}
                    }
                }
                cur_frm.refresh_field("qc_options");
                cur_frm.refresh_field("quality_check_item");
            })
            cur_frm.refresh_field('readings');

        }
    })
});

frappe.ui.form.on("Quality Inspection Reading", "quality_check_item", function(frm, cdt, cdn){
  var child = locals[cdt];

  $.each( child, function( key, value ) {
    var grid_row = cur_frm.fields_dict['readings'].grid.grid_rows_by_docname[key],
    field = frappe.utils.filter_dict(grid_row.docfields, {fieldname: "qc_options"})[0];
    var row_field = grid_row.columns_list[1].field;
    row_field.get_query =  function(){
        return {
            filters: { parent: value.quality_check_item}
        }
    }
    grid_row.refresh_field("quality_check_item");
  });
});

cur_frm.set_query("batch_no", function(doc) {
	return {
		filters: {
			"item": doc.item_code
		}
	}
})

cur_frm.add_fetch('item_code', 'item_name', 'item_name');
cur_frm.add_fetch('item_code', 'description', 'description');

