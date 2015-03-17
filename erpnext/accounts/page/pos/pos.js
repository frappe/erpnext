frappe.pages['pos'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Start Point-of-Sale (POS)'),
		single_column: true
	});

	page.main.html(frappe.render_template("pos_page", {}));

	var pos_type = frappe.ui.form.make_control({
		parent: page.main.find(".select-type"),
		df: {
			fieldtype: "Select",
			options: [
				{label: __("Billing (Sales Invoice)"), value:"Sales Invoice"},
				{value:"Sales Order"},
				{value:"Delivery Note"},
				{value:"Quotation"},
				{value:"Purchase Order"},
				{value:"Purchase Receipt"},
				{value:"Purchase Invoice"},
			],
			fieldname: "pos_type"
		},
		only_input: true
	});

	pos_type.refresh();

	pos_type.set_input("Sales Invoice");

	page.main.find(".btn-primary").on("click", function() {
		erpnext.open_as_pos = true;
		new_doc(pos_type.get_value());
	});

	$.ajax({
		url: "/api/resource/POS Setting",
		success: function(data) {
			if(!data.data.length) {
				page.main.find(".pos-setting-message").removeClass('hide');
			}
		}
	})

}
