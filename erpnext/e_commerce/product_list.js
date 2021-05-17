erpnext.ProductList = class {
	/* Options:
		- items: Items
		- settings: E Commerce Settings
		- products_section: Products Wrapper
		- preference: If preference is not list view, render but hide
	*/
	constructor(options) {
		Object.assign(this, options);

		if (this.preference !== "List View") {
			this.products_section.addClass("hidden");
		}

		this.make();
	}

	make() {
		let me = this;
		let html = `<br><br>`;

		this.items.forEach(item => {
			let title = item.web_item_name || item.item_name || item.item_code || "";
			title =  title.length > 200 ? title.substr(0, 200) + "..." : title;

			html += `<div class='row mt-6 w-100' style="border-bottom: 1px solid var(--table-border-color); padding-bottom: 1rem;">`;
			html += me.get_image_html(item, title);
			html += me.get_row_body_html(item, title, me.settings);
			html += `</div>`;
		});

		let $product_wrapper = this.products_section;
		$product_wrapper.append(html);
	}

	get_image_html(item, title) {
		let image = item.website_image || item.image;

		if (image) {
			return `
				<div class="col-2 border text-center rounded product-image" style="overflow: hidden; max-height: 200px;">
					<a class="product-link product-list-link" href="/${ item.route || '#' }">
						<img itemprop="image" class="website-image h-100 w-100" alt="${ title }"
							src="${ image }">
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

	get_row_body_html(item, title, settings) {
		let body_html = `<div class='col-9 text-left'>`;
		body_html += this.get_title_html(item, title, settings);
		body_html += this.get_item_details(item, settings);
		body_html += `</div>`;
		return body_html;
	}

	get_title_html(item, title, settings) {
		let title_html = `<div style="display: flex; margin-left: -15px;">`;
		title_html += `
			<div class="col-8" style="margin-right: -15px;">
				<a class="" href="/${ item.route || '#' }"
					style="color: var(--gray-800); font-weight: 500;">
					${ title }
				</a>
		`;

		if (item.in_stock && settings.show_stock_availability) {
			title_html += `<span class="indicator ${ item.in_stock } card-indicator"></span>`;
		}
		title_html += `</div>`;

		if (settings.enable_wishlist || settings.enabled) {
			title_html += `<div class="col-4" style="display:flex">`;
			if (!item.has_variants && settings.enable_wishlist) {
				title_html += this.get_wishlist_icon(item);
			}
			title_html += this.get_primary_button(item, settings);
			title_html += `</div>`;
		}
		title_html += `</div>`;

		return title_html;
	}

	get_item_details(item) {
		let details = `
			<p class="product-code">
				Item Code : ${ item.item_code }
			</p>
			<div class="text-muted mt-2">
				${ item.description || '' }
			</div>
			<div class="product-price">
				${ item.formatted_price || '' }
		`;

		if (item.formatted_mrp) {
			details += `
				<small class="ml-1 text-muted">
					<s>${ item.formatted_mrp }</s>
				</small>
				<small class="ml-1" style="color: #F47A7A; font-weight: 500;">
					${ item.discount } OFF
				</small>
			`;
		}
		details += `</div>`;

		return details;
	}

	get_wishlist_icon(item) {
		let icon_class = item.wished ? "wished" : "not-wished";

		return `
			<div class="like-action mr-4"
			data-item-code="${ item.item_code }"
			data-price="${ item.price || '' }"
			data-formatted-price="${ item.formatted_price || '' }">
				<svg class="icon sm">
					<use class="${ icon_class } wish-icon" href="#icon-heart"></use>
				</svg>
			</div>
		`;
	}

	get_primary_button(item, settings) {
		if (item.has_variants) {
			return `
				<a href="/${ item.route || '#' }">
					<div class="btn btn-sm btn-explore-variants" style="margin-bottom: 0; margin-top: 4px; max-height: 30px;">
						${ __('Explore') }
					</div>
				</a>
			`;
		} else if (settings.enabled && (settings.allow_items_not_in_stock || item.in_stock !== "red")) {
			return `
				<div id="${ item.name }" class="btn
					btn-sm btn-add-to-cart-list not-added"
					data-item-code="${ item.item_code }"
					style="margin-bottom: 0; margin-top: 0px; max-height: 30px;">
					${ __('Add to Cart') }
				</div>
			`;
		}
	}

};