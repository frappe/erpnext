// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleReceiptController = erpnext.vehicles.VehicleTransactionController.extend({
	refresh: function () {
		this._super();
		this.show_stock_ledger();
		this.make_checklist();
	},

	setup_queries: function () {
		this._super();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {};

			if (cint(me.frm.doc.is_return)) {
				filters['warehouse'] = ['is', 'set'];
				filters['purchase_document_no'] = ['is', 'set'];
			} else {
				filters['warehouse'] = ['is', 'not set'];
			}

			if (me.frm.doc.supplier) {
				filters['supplier'] = ['in', ['', me.frm.doc.supplier]];
			}

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			var filters = {};

			if (cint(me.frm.doc.is_return)) {
				filters['delivery_status'] = 'In Stock';
			} else {
				filters['delivery_status'] = 'Not Received';
			}

			filters['status'] = ['!=', 'Cancelled Booking'];
			filters['docstatus'] = 1;

			return {
				filters: filters
			};
		});
	},

	vehicle_checklist_add: function () {
		this.refresh_checklist();
	},
	vehicle_checklist_remove: function () {
		this.refresh_checklist();
	},
	checklist_item: function () {
		this.refresh_checklist();
	},
	checklist_item_checked: function () {
		this.refresh_checklist();
	},

	make_checklist: function () {
		$(this.frm.fields_dict.vehicle_checklist_html.wrapper).empty();
		$(`<label class="control-label">Checklist</label>`).appendTo(this.frm.fields_dict.vehicle_checklist_html.wrapper);
		var checklist_area = $('<div></div>').appendTo(this.frm.fields_dict.vehicle_checklist_html.wrapper);
		this.frm.vehicle_checklist_editor = new erpnext.vehicles.VehicleChecklistEditor(this.frm, checklist_area);
	},

	refresh_checklist: function () {
		if (this.frm.vehicle_checklist_editor) {
			this.frm.vehicle_checklist_editor.make();
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleReceiptController({frm: cur_frm}));

erpnext.vehicles.VehicleChecklistEditor = Class.extend({
	init: function(frm, wrapper, read_only) {
		var me = this;
		me.wrapper = $(wrapper);
		me.checklist_wrapper = $(`<div class="row vehicle-checklist"></div>`).appendTo(me.wrapper);
		me.left_container = $(`<div class="col-sm-6"></div>`).appendTo(me.checklist_wrapper);
		me.right_container = $(`<div class="col-sm-6"></div>`).appendTo(me.checklist_wrapper);
		me.buttons_container = $(`<div style="margin-top: 5px;"></div>`).appendTo(me.wrapper);

		me.frm = frm;
		me.read_only = cint(read_only);

		if (me.frm.doc.docstatus == 0 && (!me.frm.doc.vehicle_checklist || !me.frm.doc.vehicle_checklist.length)) {
			me.load_items_and_make();
		} else {
			me.make();
		}
	},

	clear: function () {
		this.left_container.empty();
		this.right_container.empty();
		this.buttons_container.empty();
	},

	load_items_and_make: function () {
		var me = this;
		frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_receipt.vehicle_receipt.get_vehicle_checklist_default_items",
			callback: function (r) {
				if (r.message && !r.exc) {
					$.each(r.message || [], function (i, item) {
						me.frm.add_child('vehicle_checklist', {"checklist_item": item, "checklist_item_checked": 0});
					});
					me.make();
				}
			}
		});
	},

	make: function() {
		var me = this;
		this.clear();

		var count = (me.frm.doc.vehicle_checklist || []).length;
		if (count) {
			$.each(me.frm.doc.vehicle_checklist || [], function (i, d) {
				if (i < me.frm.doc.vehicle_checklist.length / 2) {
					me.make_checkbox(d.checklist_item, me.left_container);
				} else {
					me.make_checkbox(d.checklist_item, me.right_container);
				}
			});

			me.refresh();

			if (me.can_write()) {
				me.make_buttons();
				me.bind();
			}
		}
	},

	make_checkbox: function(item, container) {
		if (!item) {
			return;
		}

		var label = frappe.utils.escape_html(item);
		var data_checklist_item = item.replace('"', '\\"');

		var wrapper = `
			<div class="checkbox" style="margin-top: 8px; margin-bottom: 8px;">
				<label>%(checklist_html)s</label>
			</div>
		`;

		var checklist_html;
		if (this.can_write()) {
			checklist_html = `
				<input type="checkbox" class="vehicle-checklist-check" data-checklist-item="${data_checklist_item}">
				${label}
			`;
		} else {
			checklist_html = `
				<span class="vehicle-checklist-check" data-checklist-item="${data_checklist_item}"></span>
				<span>${label}</span>
			`;
		}

		$(repl(wrapper, {checklist_html: checklist_html})).appendTo(container);
	},

	make_buttons: function () {
		$(`<button type="button" class="btn btn-light btn-sm add-checklist-item">
			${__('Add Checklist Item')}
		</button>`).appendTo(this.buttons_container);
	},

	refresh: function () {
		var me = this;
		me.wrapper.find(".vehicle-checklist-check").prop("checked", false);
		$.each(me.frm.doc.vehicle_checklist || [], function(i, d) {
			if (d.checklist_item) {
				var el = me.wrapper.find(`.vehicle-checklist-check[data-checklist-item='${d.checklist_item.replace("'", "\\'")}']`);
				if (me.can_write()) {
					el.prop("checked", !!d.checklist_item_checked);
				} else {
					el.html(frappe.format(d.checklist_item_checked, {'fieldtype': 'Check'}));
				}
			}
		});
	},

	bind: function() {
		var me = this;
		me.checklist_wrapper.on("change", ".vehicle-checklist-check", function() {
			me.on_check(this);
		});

		me.buttons_container.on("click", ".add-checklist-item", function () {
			me.on_add_checklist_item();
		});
	},

	on_check: function (el) {
		var me = this;

		var checklist_item = $(el).attr('data-checklist-item');
		var checked = cint($(el).prop("checked"));

		var found = false;
		$.each(me.frm.doc.vehicle_checklist || [], function(i, d) {
			if (d.checklist_item == checklist_item) {
				d.checklist_item_checked = checked;
				found = true;
			}
		});

		if (!found && checked) {
			me.frm.add_child('vehicle_checklist', {"checklist_item": checklist_item, "checklist_item_checked": checked});
		}

		me.frm.dirty();
	},

	on_add_checklist_item: function () {
		var me = this;
		frappe.prompt('Checklist Item', ({ value }) => {
			var exists = (me.frm.doc.vehicle_checklist || []).filter(d => d.checklist_item == value);
			if (exists.length) {
				frappe.throw(__("<b>{0}</b> Checklist Item already exists", [value]));
			} else {
				me.frm.add_child('vehicle_checklist', {"checklist_item": value,
					"checklist_item_checked": 1, "is_custom_checklist_item": 1});
				me.make();
			}
		});
	},

	can_write: function () {
		return !this.read_only && this.frm.doc.docstatus == 0 && frappe.model.can_write(this.frm.doc.doctype);
	},
});
