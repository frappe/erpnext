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

	// route
	if (!item.route) {
		item.route = `marketplace/item/${item.hub_item_code}`
	}

	const item_html = `
		<div class="col-md-3 col-sm-4 col-xs-6 hub-card-container">
			<div class="hub-card"
				data-hub-item-code="${item.hub_item_code}"
				data-route="${item.route}">

				<div class="hub-card-header level">
					<div class="ellipsis">
						<div class="hub-card-title ellipsis bold">${title}</div>
						<div class="hub-card-subtitle ellipsis text-muted">${subtitle}</div>
					</div>
					<i class="octicon octicon-x text-extra-muted"
						data-hub-item-code="${item.hub_item_code}">
					</i>
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

	if (company_name) {
		subtitle.push(company_name);
	}

	let dot_spacer = '<span aria-hidden="true"> · </span>';
	subtitle = subtitle.join(dot_spacer);

	const edit_item_button = `<div class="hub-card-overlay-button" data-route="Form/Item/${item.item_name}">
		<button class="btn btn-default zoom-view">
			<i class="octicon octicon-pencil text-muted"></i>
		</button>
	</div>`;

	const item_html = `
		<div class="col-md-3 col-sm-4 col-xs-6 hub-card-container">
			<div class="hub-card is-local ${is_active ? 'active' : ''}" data-id="${id}">
				<div class="hub-card-header flex">
					<div class="ellipsis">
						<div class="hub-card-title ellipsis bold">${title}</div>
						<div class="hub-card-subtitle ellipsis text-muted">${subtitle}</div>
					</div>
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

function get_buying_item_message_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);

	const message = item.recent_message
	const sender = message.sender === frappe.session.user ? 'You' : message.sender
	const content = strip_html(message.content)

	// route
	item.route = `marketplace/buying/${item.hub_item_code}`

	const item_html = `
		<div class="col-md-7">
			<div class="hub-list-item" data-route="${item.route}">
				<div class="hub-list-left">
					<img class="hub-list-image" src="${item.image}">
					<div class="hub-list-body ellipsis">
						<div class="hub-list-title">${item_name}</div>
						<div class="hub-list-subtitle ellipsis">
							<span>${sender}: </span>
							<span>${content}</span>
						</div>
					</div>
				</div>
				<div class="hub-list-right">
					<span class="text-muted">${comment_when(message.creation, true)}</span>
				</div>
			</div>
		</div>
	`;

	return item_html;
}

function get_selling_item_message_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);

	// route
	if (!item.route) {
		item.route = `marketplace/item/${item.hub_item_code}`
	}

	let received_messages = '';
	item.received_messages.forEach(message => {
		const sender = message.sender === frappe.session.user ? 'You' : message.sender
		const content = strip_html(message.content)

		received_messages += `
			<div class="received-message">
				<span class="text-muted">${comment_when(message.creation, true)}</span>
				<div class="ellipsis">
					<span class="bold">${sender}: </span>
					<span>${content}</span>
				</div>
			</div>
		`
	});

	const item_html = `
		<div class="selling-item-message-card">
			<div class="selling-item-detail" data-route="${item.route}">
				<img class="item-image" src="${item.image}">
				<h5 class="item-name">${item_name}</h5>
				<div class="received-message-container">
					${received_messages}
				</div>
			</div>
		</div>
	`;

	return item_html;
}

export {
	get_item_card_html,
	get_local_item_card_html,
	get_buying_item_message_card_html,
	get_selling_item_message_card_html
}
