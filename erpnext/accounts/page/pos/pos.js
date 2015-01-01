frappe.pages['pos'].onload = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Start POS'),
		single_column: true
	});

	page.main.html('<div class="text-center" style="padding: 40px">\
		<p>' + __("Select type of transaction") + '</p>\
		<p class="select-type" style="margin: auto; max-width: 300px; margin-bottom: 15px;"></p>\
		<p class="pos-setting-message hide">'
			+ '<br><a class="btn btn-default btn-sm" onclick="newdoc(\'POS Setting\')">'
			+ __("Make new POS Setting") + '</a><br><br></p>\
		<p><button class="btn btn-primary btn-sm">' + __("Start") + '</button></p>\
	</div>');

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
