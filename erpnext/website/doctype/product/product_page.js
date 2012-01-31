wn.require('erpnext/website/js/product_category.js');

pscript["onload_{{ doc.page_name }}"] = function(wrapper) {
	erpnext.make_product_categories(wrapper);
	$(wrapper).find('.product-inquiry').click(function() {
		loadpage('contact', function() {
			$('#content-contact-us [name="contact-message"]').val("Hello,\n\n\
			Please send me more information on {{ doc.title }} (Item Code:{{ doc.item }})\n\n\
			My contact details are:\n\nThank you!\
			");
		})
	})
}