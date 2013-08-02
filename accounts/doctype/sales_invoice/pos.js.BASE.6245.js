erpnext.POS = Class.extend({
	init: function(wrapper, frm) {
		this.wrapper = wrapper;
		this.frm = frm;
		this.wrapper.html('<div class="customer-area"></div>\
			<div class="item-area"></div>\
			<div><button class="btn btn-default btn-add">Add</button>');
		
		this.make();

		var me = this;
		$(this.frm.wrapper).on("refresh-fields", function() {
			me.refresh();
		});

	},
	make: function() {
		this.make_customer();
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
	make_items: function() {
		var me = this;
		this.wrapper.find(".btn-add").click(function() {
			var child = wn.model.add_child(me.frm.doc, "Sales Invoice Item", "entries");
			child.item_code = "Test Item";
			me.frm.cscript.item_code(me.frm.doc, child.doctype, child.name);
		});
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