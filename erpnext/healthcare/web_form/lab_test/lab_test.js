frappe.ready(function() {
	//	bind events here
	var normal_test_items = $('div[data-fieldname = "normal_test_items"]');
	var normal_test_items_add_btn = $('button[data-fieldname = "normal_test_items"]');
	var special_test_items = $('div[data-fieldname = "special_test_items"]');
	var special_test_items_add_btn = $('button[data-fieldname = "special_test_items"]');
	var sensitivity_test_items = $('div[data-fieldname = "sensitivity_test_items"]');
	var sensitivity_test_items_add_btn = $('button[data-fieldname = "sensitivity_test_items"]');
	var sensitivity_toggle = $('input[name = "sensitivity_toggle"]');
	var special_toggle = $('input[name = "special_toggle"]');
	var normal_toggle = $('input[name = "normal_toggle"]');
	if(normal_toggle.val() == 1){
		//	normal_test_items[0].style.display = "none";
		//	normal_test_items[0].setAttribute("hidden", true);
		//	normal_test_items_add_btn[0].style.visibility = "hidden";
		special_test_items[0].style.display = "none";
		special_test_items_add_btn[0].style.display = "none";
		sensitivity_test_items[0].style.display = "none";
		sensitivity_test_items_add_btn[0].style.display = "none";
		normal_test_items_add_btn[0].style.display = "none";
	}else if(sensitivity_toggle.val() == 1){
		special_test_items[0].style.display = "none";
		special_test_items_add_btn[0].style.display = "none";
		normal_test_items[0].style.display = "none";
		normal_test_items_add_btn[0].style.display = "none";
		sensitivity_test_items_add_btn[0].style.display = "none";
	}else if(special_toggle.val() == 1){
		normal_test_items[0].style.display = "none";
		normal_test_items_add_btn[0].style.display = "none";
		sensitivity_test_items[0].style.display = "none";
		sensitivity_test_items_add_btn[0].style.display = "none";
		special_test_items_add_btn[0].style.display = "none";
	}
});
