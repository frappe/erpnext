function make_search_bar({wrapper, on_search, placeholder = __('Search for anything')}) {
	const $search = $(`
		<div class="hub-search-container">
			<input type="text" class="form-control" placeholder="${placeholder}">
		</div>`
	);
	wrapper.append($search);
	const $search_input = $search.find('input');

	$search_input.on('keydown', frappe.utils.debounce((e) => {
		if (e.which === frappe.ui.keyCode.ENTER) {
			const search_value = $search_input.val();
			on_search(search_value);
		}
	}, 300));
}

export {
    make_search_bar
}
