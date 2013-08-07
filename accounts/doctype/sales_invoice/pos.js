// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

erpnext.POS = Class.extend({
	init: function(wrapper, frm) {
		this.wrapper = wrapper;
		this.frm = frm;
		this.wrapper.html('<div class="container">\
			<div class="row">\
				<div class="col-lg-3">\
					<div class="customer-area"></div>\
					<div class="button-area">\
						<div class="col-lg-4">\
							<a class="btn btn-danger col-lg-12">\
							<i class="icon-trash icon-large"></i></a></div>\
						<div class="col-lg-4">\
							<a class="btn btn-primary col-lg-12">\
							<i class="icon-barcode icon-large"></i></a></div>\
						<div class="col-lg-4">\
							<a class="btn btn-success col-lg-12">\
							<i class="icon-money icon-large"></i></a></div>\
					</div>\
					<div>&nbsp;</div>\
					<div class="item-cart"></div>\
				</div>\
				<div class="col-lg-9">\
					<div class="col-lg-6">\
						<div class="item-group-area"></div></div>\
					<div class="col-lg-6">\
						<div class="search-area"></div></div>\
				</div>\
			</div></div>');

		this.make();

		var me = this;
		$(this.frm.wrapper).on("refresh-fields", function() {
			me.refresh();
		});

	},
	make: function() {
		this.make_customer();
		this.make_item_group();
		this.make_search();
		this.make_items();
	},
	make_customer: function() {
		var me = this;
		this.customer = wn.ui.form.make_control({
			df: {
				"fieldtype": "Link",
				"options": "Customer",
				"label": "Customer",
				"fieldname": "pos_customer"
			},
			parent: this.wrapper.find(".customer-area")
		});
		this.customer.make_input();
		this.customer.$input.on("change", function() {
			if(!me.customer.autocomplete_open)
				wn.model.set_value("Sales Invoice", me.frm.docname, "customer", this.value);
		});
	},
	make_item_group: function() {
		var me = this;
		this.item_group = wn.ui.form.make_control({
			df: {
				"fieldtype": "Link",
				"options": "Item Group",
				"label": "Item Group",
				"fieldname": "pos_item_group"
			},
			parent: this.wrapper.find(".item-group-area")
		});
		this.item_group.make_input();
		// this.customer.$input.on("change", function() {
		// 	if(!me.customer.autocomplete_open)
		// 		wn.model.set_value("Sales Invoice", me.frm.docname, "customer", this.value);
		// });
	},
	make_search: function() {
		var me = this;
		this.search = wn.ui.form.make_control({
			df: {
				"fieldtype": "Link",
				"options": "Item",
				"label": "Item",
				"fieldname": "pos_item"
			},
			parent: this.wrapper.find(".search-area")
		});
		this.search.make_input();
		// this.customer.$input.on("change", function() {
		// 	if(!me.customer.autocomplete_open)
		// 		wn.model.set_value("Sales Invoice", me.frm.docname, "customer", this.value);
		// });
	},
	make_items: function() {
		var me = this;
		var $cart = me.wrapper.find(".item-cart")
		$(repl("<div class='col-lg-12'><div class='panel' style='min-height:250px;'>\
			<div class='panel-heading' style='font-size:14px;min-height:40px;'>\
				<div class='col-lg-3'>Item</div>\
				<div class='col-lg-3'>#</div>\
				<div class='col-lg-3'>Rate</div>\
				<div class='col-lg-3'>Amount</div>\
			</div></div></div>")).appendTo($cart);

		// this.wrapper.find(".btn-add").click(function() {
		// 	var child = wn.model.add_child(me.frm.doc, "Sales Invoice Item", "entries");
		// 	child.item_code = "I - 1";
		// 	me.frm.cscript.item_code(me.frm.doc, child.doctype, child.name);
		// });
	},
	refresh: function() {
		var me = this;
		this.customer.set_input(this.frm.doc.customer);

		// add items
		var $items = me.wrapper.find(".item-area").empty();
		$.each(wn.model.get_children("Sales Invoice Item", this.frm.doc.name, "entries", 
			"Sales Invoice"), function(i, d) {
				$(repl("<div>%(item_code)s</div>", d)).appendTo($items);
			});
	}
})