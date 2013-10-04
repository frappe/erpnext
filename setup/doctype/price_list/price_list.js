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
	
	$(cur_frm.fields_dict.item_prices_html.wrapper).empty();
	
	new wn.ui.form.TableGrid({
		parent: cur_frm.fields_dict.item_prices_html.wrapper,
		frm: cur_frm,
		table_field: wn.meta.get_docfield("Price List", "item_prices", cur_frm.doc.name)
	});
}

wn.ui.form.TableGrid = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
		this.fields = wn.meta.get_docfields("Item Price", cur_frm.doc.name);
		this.make_table();
	},
	make_table: function() {
		var me = this;
		// Creating table & assigning attributes
		var grid_table = document.createElement("table");
		grid_table.className = "table table-hover table-bordered table-grid";
		
		// Appending header & rows to table
		grid_table.appendChild(this.make_table_headers());
		grid_table.appendChild(this.make_table_rows());
				
		// Creating button to add new row
		var btn_div = document.createElement("div");
		var new_row_btn = document.createElement("button");
		new_row_btn.className = "btn btn-success table-new-row";
		new_row_btn.title = "Add new row";

		var btn_icon = document.createElement("i");
		btn_icon.className = "icon-plus";
		new_row_btn.appendChild(btn_icon);
		new_row_btn.innerHTML += " Add new row";
		btn_div.appendChild(new_row_btn);

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
		row.className = "active";
		
		// Creating head first cell
		var th = document.createElement("th");
		th.width = "8%";
		th.className = "text-center";
		th.innerHTML = "#";
		row.appendChild(th);

		// Make other headers with label as heading
		for(var i=0, l=this.fields.length; i<l; i++) {
			var df = this.fields[i];
			
			if(!!!df.hidden && df.in_list_view === 1) {
				var th = document.createElement("th");
			
				// If currency then move header to right
				if(["Int", "Currency", "Float"].indexOf(df.fieldtype) !== -1) th.className = "text-right";
			
				th.innerHTML = wn._(df.label);
				row.appendChild(th);
			}
		}
		
		header.appendChild(row);

		return header;
	},
	make_table_rows: function() {
		var me = this;

		// Creating table body
		var table_body = document.createElement("tbody");

		var item_prices = wn.model.get_children(this.table_field.options, this.frm.doc.name, 
			this.table_field.fieldname, this.frm.doctype);
			
		for(var i=0, l=item_prices.length; i<l; i++) {
			var d = item_prices[i];
			
			// Creating table row
			var tr = this.add_new_row(d);
			
			// append row to table body
			table_body.appendChild(tr);
		}
		
		this.table_body = table_body;
		
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

		$a(this.dialog.body, 'div', '', '', this.make_dialog_buttons(row));
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
			dialog_values[item.fieldname] = $(row).find('td[data-fieldname="'+ item.fieldname +'"]').attr('data-fieldvalue');
		});

		return dialog_values;
	},
	make_dialog_buttons: function(row) {
		var me = this;
		var buttons = '<button class="btn btn-primary update">Update</button>';

		// if user can delete then only add the delete button in dialog
		if (wn.model.can_delete(me.frm.doc.doctype) && row)
			buttons += ' <button class="btn btn-default delete">Delete</button>';

		return buttons;
	},
	update_row: function(row) {
		var me = this;

		if (!row) {
			var d = wn.model.add_child(this.frm.doc, this.table_field.options, 
				this.table_field.fieldname);
			refresh_field(this.table_field.fieldname);
			this.update_item_price(d.name);
			var tr = this.add_new_row(d);
			this.table_body.appendChild(tr);
		}
		else {
			this.update_item_price(null, row);
		}
		
		this.dialog.hide();
	},
	
	update_item_price: function(docname, row) {
		var me = this;
		if(!docname && row) docname = $(row).attr("data-docname");
		$.each(me.fields, function(i, df) {
			var val = me.dialog.get_values()[df.fieldname];
			
			if(["Currency", "Float"].indexOf(df.fieldtype)!==-1) {
				val = flt(val);
			} else if(["Int", "Check"].indexOf(df.fieldtype)!==-1) {
				val = cint(val);
			}
			
			wn.model.set_value(me.table_field.options, docname, 
				df.fieldname, val);
				
			if(row) {
				var $td = $(row).find('td[data-fieldname="'+ df.fieldname +'"]');
				$td.attr('data-fieldvalue', val);
				// If field type is currency the update with format currency
				$td.html(wn.format(val, df));
			}
		});
	},
	
	delete_row: function(row) {
		var me = this;
		var docname = $(row).find('td:last').attr('data-docname');
		wn.model.clear_doc(me.table_field.options, docname);
		$(row).remove();

		// Re-assign idx
		$.each($(this.parent).find("tbody tr"), function(idx, data) {
			var $td = $(data).find('td:first');
			$td.html(idx + 1);
		});
		this.dialog.hide();
	},
	
	add_new_row: function(d) {
		var tr = document.createElement("tr");
		tr.className = "table-row";
		tr.setAttribute("data-docname", d.name);
		
		// Creating table data & appending to row
		var td = document.createElement("td");
		td.className = "text-center";
		td.innerHTML = d.idx;
		tr.appendChild(td);
		
		for(var f=0, lf=this.fields.length; f<lf; f++) {
			var df = this.fields[f];
			if(!!!df.hidden && df.in_list_view===1) {
				var td = document.createElement("td");
				td.setAttribute("data-fieldname", df.fieldname);
				td.setAttribute("data-fieldvalue", d[df.fieldname]);
				td.setAttribute("data-docname", d.name);
				
				// If currency then move header to right
				if(["Int", "Currency", "Float"].indexOf(df.fieldtype) !== -1) {
					td.className = "text-right";
				}
				
				// format and set display
				td.innerHTML = wn.format(d[df.fieldname], df);
				
				// append column to tabel row
				tr.appendChild(td);
			}
		}
		return tr;
	}
});