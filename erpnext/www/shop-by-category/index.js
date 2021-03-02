$(() => {
	$('.category-card').on('click', (e) => {
		let category_type = e.currentTarget.dataset.type;
		let category_name = e.currentTarget.dataset.name;

		if (category_type != "item_group") {
			let filters = {};
			filters[category_type] =  [category_name];
			window.location.href = "/all-products?field_filters=" + JSON.stringify(filters);
		}
	});
});