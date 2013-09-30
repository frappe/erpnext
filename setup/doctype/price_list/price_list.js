// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function() {
		erpnext.add_for_territory();
	},
});

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.show_item_prices();
}

cur_frm.cscript.show_item_prices = function() {
	var item_price = wn.model.get("Item Price", {parent: cur_frm.doc.name});
	var show = item_price && item_price.length;

	cur_frm.toggle_display("item_prices", show);
	$(cur_frm.fields_dict.item_prices.wrapper).empty();
	if (!show) return;
	
	new wn.ui.form.TableGrid({
		parent: cur_frm.fields_dict.item_prices.wrapper,
		frm: cur_frm,
		table_field: wn.model.get("DocField", {parent:"Price List", fieldname:"item_prices"})[0]
	});
}

wn.ui.form.TableGrid = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
		this.fields = wn.model.get("DocField", {parent: this.table_field.options});
		this.make_table();
	},
	make_table: function() {
		var me = this;
		// Creating table & assigning attributes
		var grid_table = document.createElement("table");
		$(grid_table).attr("class", "table table-hover table-bordered grid");
		
		// Appending header & rows to table

		$(this.make_table_headers()).appendTo(grid_table);
		$(this.make_table_rows()).appendTo(grid_table);
				
		// Creating button to add new row
		var btn_div = document.createElement("div");
		var new_row_btn = document.createElement("button");
		$new_row_btn = $(new_row_btn);
		$new_row_btn.attr({
			"class": "btn btn-success table-new-row",
			"title": "Add new row"
		});
		var btn_icon = document.createElement("i");
		$(btn_icon).attr("class", "icon-plus");
		$(btn_icon).appendTo(new_row_btn);
		$new_row_btn.append(" Add new row");
		$new_row_btn.appendTo(btn_div);

		// Appending table & button to parent
		var $grid_table = $(grid_table).appendTo($(this.parent));
		var $btn_div = $(btn_div).appendTo($(this.parent));

		$btn_div.on("click", ".table-new-row", function() {
			me.make_dialog();
			return false;
		});

		$grid_table.on("click", ".table-row", function() {
			me.make_dialog(this);
			return false;
		});
	},
	make_table_headers: function() {
		var me = this;
		var header = document.createElement("thead");
		
		// Creating header row
		var row = document.createElement("tr");
		$(row).attr({
			"class": "active",
			"style": "height:50px"
		});
		$(row).appendTo(header);

		// Creating head first cell
		var th = document.createElement("th");
		$(th).attr({
			"width": "8%",
			"style": "vertical-align:middle",
			"class": "text-center"
		});
		$(th).html("#");
		$(th).appendTo(row);

		// Make other headers with label as heading
		$.each(this.fields, function(i, obj) {
			if (obj.in_list_view===1)
				var th = document.createElement("th");
				$(th).attr("style", "vertical-align:middle");
				$(th).html(obj.label);
				$(th).appendTo(row);
		});

		return header;
	},
	make_table_rows: function() {
		var me = this;

		// Creating table body
		var table_body = document.createElement("tbody");
		$(table_body).attr("style", "cursor:pointer");

		$.each(wn.model.get_children(this.table_field.options, this.frm.doc.name, 
			this.table_field.fieldname, this.frm.doctype), function(index, d) {

				// Creating table row
				var tr = document.createElement("tr");
				$(tr).attr({
					"class": "table-row",
					"data-idx": d.idx
				});

				// Creating table data & appending to row
				var td = document.createElement("td");
				$(td).attr("class", "text-center");
				$(td).html(d.idx);
				$(td).appendTo(tr);

				$.each(me.fields, function(i, obj) {
					if (obj.in_list_view===1) {
						var td = document.createElement("td");
						$(td).attr({
							"data-fieldtype": obj.fieldtype,
							"data-fieldname": obj.fieldname,
							"data-fieldvalue": d[obj.fieldname],
							"data-doc_name": d["name"]
						});
						$(td).html(d[obj.fieldname]);
						
						// if field is currency then add style & change text
						if (obj.fieldtype=="Currency") {
							$(td).attr("style", "text-align:right");
							$(td).html(format_currency(d[obj.fieldname], me.frm.doc.currency));
						}
						
						// Append td to row
						$(td).appendTo(tr);
					}
				});

				// Append row to table body
				$(tr).appendTo(table_body);
		});
		
		return table_body;
	},
	make_dialog: function(row) {
		var me = this;

		this.dialog = new wn.ui.Dialog({
			title: this.table_field.options, 
			fields: this.fields
		});

		if (row)
			this.dialog.set_values(this.make_dialog_values(row));

		$a(this.dialog.body, 'div', '', '', this.make_dialog_buttons());
		this.dialog.show();

		this.dialog.$wrapper.find('button.update').on('click', function() {
			me.update_row(row);
		});

		this.dialog.$wrapper.find('button.delete').on('click', function() {
			me.delete_row(row);
		});
		return row;
	},
	make_dialog_values: function(row) {
		var me = this;
		var dialog_values = {};

		$.each(this.fields, function(i, item) {
			dialog_values[item.fieldname] = $(row).find('td[data-fieldname="'+ item.fieldname +'"]').data('fieldvalue');
		});

		return dialog_values;
	},
	make_dialog_buttons: function() {
		var me = this;
		var buttons = '<button class="btn btn-primary update">Update</button>';

		// if user can delete then only add the delete button in dialog
		if (wn.model.can_delete(me.frm.doc.doctype))
			buttons += ' <button class="btn btn-default delete">Delete</button>';

		return buttons;
	},
	update_row: function(row) {
		var me = this;

		if (!row) {
			me.add_new_row();
		}
		else {
			$.each(me.fields, function(i, item) {
				var $td = $(row).find('td[data-fieldname="'+ item.fieldname +'"]');
				var val = me.dialog.get_values()[item.fieldname];
				
				wn.model.set_value(me.table_field.options, $td.attr('data-doc_name'), 
					item.fieldname, me.dialog.get_values()[item.fieldname]);
				$td.attr('data-fieldvalue', val);
				
				// If field type is currency the update with format currency
				if ($td.attr('data-fieldtype') == "Currency")
					$td.html(format_currency(val, me.frm.doc.currency));
				else
					$td.html(val);
			});
		}
		
		this.dialog.hide();
	},
	delete_row: function(row) {
		var me = this;
		var doc_name = $(row).find('td:last').attr('data-doc_name');
		wn.model.clear_doc(me.table_field.options, doc_name);
		$(row).remove();

		// Re-assign idx
		$.each($(this.parent).find(".grid tbody tr"), function(idx, data) {
			$(data).attr("data-idx", idx + 1);
			var $td = $(data).find('td:first');
			$td.html(idx + 1);
		});
		this.dialog.hide();
	},
	add_new_row: function() {
		var me = this;
		var row = $(this.parent).find(".grid tbody tr");

		// Creating new row
		var new_row = document.createElement("tr");
		$(new_row).attr({
			"class": "table-row",
			"data-idx": row.length + 1
		});

		// Creating first table data
		var td = document.createElement("td");
		$(td).attr("class", "text-center");
		$(td).html(row.length + 1);
		$(td).appendTo(new_row);

		var child = wn.model.add_child(this.frm.doc, this.table_field.options, 
			this.table_field.fieldname);
		
		$.each(this.fields, function(i, obj) {
			if (obj.in_list_view===1) {
				child[obj.fieldname] = me.dialog.get_values()[obj.fieldname];
				
				var td = document.createElement("td");
				$(td).attr({
					"data-fieldtype": obj.fieldtype,
					"data-fieldname": obj.fieldname,
					"data-fieldvalue": child[obj.fieldname],
					"data-doc_name": child["name"]
				});
				$(td).html(child[obj.fieldname]);
				
				// if field is currency then add style & change text
				if (obj.fieldtype=="Currency") {
					$(td).attr("style", "text-align:right");
					$(td).html(format_currency(child[obj.fieldname], me.frm.doc.currency));
				}
				
				// Append td to row
				$(td).appendTo(new_row);
			}
		});

		$(new_row).appendTo($(this.parent).find(".grid tbody"));
	}
});