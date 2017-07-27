erpnext.ItemSelector = Class.extend({
	init: function(opts) {
		$.extend(this, opts);

		this.grid = this.frm.get_field("items").grid;
		this.setup();
	},

	setup: function() {
		var me = this;
		if(!this.grid.add_items_button) {
			this.grid.add_items_button = this.grid.add_custom_button(__('Add Items'), function() {
				if(!me.dialog) {
					me.make_dialog();
				}
				me.dialog.show();
				me.render_items();
				setTimeout(function() { me.dialog.input.focus(); }, 1000);
			});
		}
	},

	make_dialog: function() {
		this.dialog = new frappe.ui.Dialog({
			title: __('Add Items')
		});
		var body = $(this.dialog.body);
		body.html('<div><p><input type="text" class="form-control"></p>\
			<br><div class="results"></div></div>');

		this.dialog.input = body.find('.form-control');
		this.dialog.results = body.find('.results');

		var me = this;
		this.dialog.results.on('click', '.pos-item', function() {
			me.add_item($(this).attr('data-name'))
		});

		this.dialog.input.on('keyup', function() {
			if(me.timeout_id) {
				clearTimeout(me.timeout_id);
			}
			me.timeout_id = setTimeout(function() {
				me.render_items();
				me.timeout_id = undefined;
			}, 500);
		});
	},

	add_item: function(item_code) {
		// add row or update qty
		var added = false;

		// find row with item if exists
		$.each(this.frm.doc.items || [], function(i, d) {
			if(d.item_code===item_code) {
				frappe.model.set_value(d.doctype, d.name, 'qty', d.qty + 1);
				frappe.show_alert(__("Added {0} ({1})", [item_code, d.qty]));
				added = true;
				return false;
			}
		});

		if(!added) {
			var d = this.grid.add_new_row();
			frappe.model.set_value(d.doctype, d.name, 'item_code', item_code);

			// after item fetch
			frappe.after_ajax(function() {
				setTimeout(function() {
					frappe.model.set_value(d.doctype, d.name, 'qty', 1);
					frappe.show_alert(__("Added {0} ({1})", [item_code, 1]));
				}, 100);
			});
		}

	},

	render_items: function() {
		var args = erpnext.queries.item();
		args.txt = this.dialog.input.val();
		args.as_dict = 1;

		var me = this;
		frappe.link_search("Item", args, function(r) {
			$.each(r.values, function(i, d) {
				if(!d.image) {
					d.abbr = frappe.get_abbr(d.item_name);
					d.color = frappe.get_palette(d.item_name);
				}
			});
			me.dialog.results.html(frappe.render_template('item_selector', {'data':r.values}));
		});
	}
})