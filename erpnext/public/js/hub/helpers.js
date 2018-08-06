function get_empty_state(message, action) {
	return `<div class="empty-state flex align-center flex-column justify-center">
		<p class="text-muted">${message}</p>
		${action ? `<p>${action}</p>`: ''}
	</div>`;
}

function get_item_card_container_html(items, title='', get_item_html = get_item_card_html) {
	const items_html = (items || []).map(item => get_item_html(item)).join('');
	const title_html = title
		? `<div class="col-sm-12 margin-bottom">
				<h4>${title}</h4>
			</div>`
		: '';

	const html = `<div class="row hub-card-container">
		${title_html}
		${items_html}
	</div>`;

	return html;
}

function get_item_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);
	const img_url = item.image;
	const company_name = item.company;

	// Subtitle
	let subtitle = [comment_when(item.creation)];
	const rating = item.average_rating;
	if (rating > 0) {
		subtitle.push(rating + `<i class='fa fa-fw fa-star-o'></i>`)
	}
	subtitle.push(company_name);

	let dot_spacer = '<span aria-hidden="true"> · </span>';
	subtitle = subtitle.join(dot_spacer);

	const item_html = `
		<div class="col-md-3 col-sm-4 col-xs-6">
			<div class="hub-card" data-route="marketplace/item/${item.hub_item_code}">
				<div class="hub-card-header">
					<div class="hub-card-title ellipsis bold">${title}</div>
					<div class="hub-card-subtitle ellipsis text-muted">${subtitle}</div>
				</div>
				<div class="hub-card-body">
					<img class="hub-card-image" src="${img_url}" />
					<div class="overlay hub-card-overlay"></div>
				</div>
			</div>
		</div>
	`;

	return item_html;
}

function get_local_item_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);
	const img_url = item.image;
	const company_name = item.company;

	const is_active = item.publish_in_hub;
	const id = item.hub_item_code || item.item_code;

	// Subtitle
	let subtitle = [comment_when(item.creation)];
	const rating = item.average_rating;
	if (rating > 0) {
		subtitle.push(rating + `<i class='fa fa-fw fa-star-o'></i>`)
	}
	subtitle.push(company_name);

	let dot_spacer = '<span aria-hidden="true"> · </span>';
	subtitle = subtitle.join(dot_spacer);

	const edit_item_button = `<div class="hub-card-overlay-button" style="right: 15px; bottom: 15px;" data-route="Form/Item/${item.item_name}">
		<button class="btn btn-default zoom-view">
			<i class="octicon octicon-pencil text-muted"></i>
		</button>
	</div>`;

	const item_html = `
		<div class="col-md-3 col-sm-4 col-xs-6">
			<div class="hub-card is-local ${is_active ? 'active' : ''}" data-id="${id}">
				<div class="hub-card-header">
					<div class="hub-card-title ellipsis bold">${title}</div>
					<div class="hub-card-subtitle ellipsis text-muted">${subtitle}</div>
					<i class="octicon octicon-check text-success"></i>
				</div>
				<div class="hub-card-body">
					<img class="hub-card-image" src="${img_url}" />
					<div class="hub-card-overlay">
						<div class="hub-card-overlay-body">
							${edit_item_button}
						</div>
					</div>
				</div>
			</div>
		</div>
	`;

	return item_html;
}


function get_rating_html(rating) {
	let rating_html = ``;
	for (var i = 0; i < 5; i++) {
		let star_class = 'fa-star';
		if (i >= rating) star_class = 'fa-star-o';
		rating_html += `<i class='fa fa-fw ${star_class} star-icon' data-index=${i}></i>`;
	}
	return rating_html;
}

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
	get_empty_state,
	get_item_card_container_html,
	get_item_card_html,
	get_local_item_card_html,
	get_rating_html,
	make_search_bar,
}
