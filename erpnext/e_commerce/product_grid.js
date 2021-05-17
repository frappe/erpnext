erpnext.ProductGrid = class {
	/* Options:
		- items: Items
		- settings: E Commerce Settings
		- products_section: Products Wrapper
		- preference: If preference is not grid view, render but hide
	*/
	constructor(options) {
		Object.assign(this, options);

		if (this.preference !== "Grid View") {
			this.products_section.addClass("hidden");
		}

		this.make();
	}

	make() {
		let me = this;
		let html = ``;

		this.items.forEach(item => {
			let title = item.web_item_name || item.item_name || item.item_code || "";
			title =  title.length > 50 ? title.substr(0, 50) + "..." : title;

			html += `<div class="col-sm-4 item-card"><div class="card text-left">`;
			html += me.get_image_html(item, title);
			html += me.get_card_body_html(item, title, me.settings);
			html += `</div></div>`;
		})

		let $product_wrapper = this.products_section;
		$product_wrapper.append(html);
	}

	get_image_html(item, title) {
		let image = item.website_image || item.image;

		if(image) {
			return `
				<div class="card-img-container">
					<a href="/${ item.route || '#' }" style="text-decoration: none;">
						<img class="card-img" src="${ image }" alt="${ title }">
					</a>
				</div>
			`;
		} else {
			return `
				<a href="/${ item.route || '#' }" style="text-decoration: none;">
					<div class="card-img-top no-image">
						${ frappe.get_abbr(title) }
					</div>
				</a>
			`;
		}
	}

	get_card_body_html(item, title, settings) {
		let body_html = `
			<div class="card-body text-left" style="width:100%">
				<div style="margin-top: 16px; display: flex;">
		`;
		body_html += this.get_title_with_indicator(item, title);

		if (!item.has_variants && settings.enable_wishlist) {
			body_html += this.get_wishlist_icon(item);
		}

		body_html += `</div>`; // close div on line 50
		body_html += `<div class="product-category">${ item.item_group || '' }</div>`;

		if (item.formatted_price) {
			body_html += this.get_price_html(item);
		}

		body_html += this.get_primary_button(item, settings);
		body_html += `</div>`; // close div on line 49

		return body_html;
	}

	get_title_with_indicator(item, title, settings) {
		let title_html = `
			<a href="/${ item.route || '#' }">
				<div class="product-title">
					${ title || '' }
		`;
		if (item.in_stock) {
			title_html += `<span class="indicator ${ item.in_stock } card-indicator"></span>`;
		}
		title_html += `</div></a>`;
		return title_html
	}

	get_wishlist_icon(item) {
		let icon_class = item.wished ? "wished" : "not-wished";
		return `
			<div class="like-action"
				data-item-code="${ item.item_code }"
				data-price="${ item.price || '' }"
				data-formatted-price="${ item.formatted_price || '' }">
				<svg class="icon sm">
					<use class="${ icon_class } wish-icon" href="#icon-heart"></use>
				</svg>
			</div>
		`;
	}

	get_price_html(item) {
		let price_html = `
			<div class="product-price">
				${ item.formatted_price || '' }
		`;

		if (item.formatted_mrp) {
			price_html += `
				<small class="ml-1 text-muted">
					<s>${ item.formatted_mrp }</s>
				</small>
				<small class="ml-1" style="color: #F47A7A; font-weight: 500;">
					${ item.discount } OFF
				</small>
			`;
		}
		price_html += `</div>`;
		return price_html;
	}

	get_primary_button(item, settings) {
		if (item.has_variants) {
			return `
				<a href="/${ item.route || '#' }">
					<div class="btn btn-sm btn-explore-variants w-100 mt-4">
						${ __('Explore') }
					</div>
				</a>
			`;
		} else if (settings.enabled && (settings.allow_items_not_in_stock || item.in_stock !== "red")) {
			return `
				<div id="${ item.name }" class="btn
					btn-sm btn-add-to-cart-list not-added w-100 mt-4"
					data-item-code="${ item.item_code }">
					${ __('Add to Cart') }
				</div>
			`;
		}
	}
}