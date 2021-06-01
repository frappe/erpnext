erpnext.ProductSearch = class {
	constructor() {
		this.MAX_RECENT_SEARCHES = 4;
		this.searchBox = $("#search-box");

		this.setupSearchDropDown();
		this.bindSearchAction();
	}

	setupSearchDropDown() {
		this.search_area = $("#dropdownMenuSearch");
		this.setupSearchResultContainer();
		this.setupProductsContainer();
		this.setupCategoryRecentsContainer();
		this.populateRecentSearches();
	}

	bindSearchAction() {
		let me = this;

		this.searchBox.on("focus", (e) => {
			this.search_dropdown.removeClass("hidden");
		});

		this.searchBox.on("focusout", (e) => {
			this.search_dropdown.addClass("hidden");
		});

		this.searchBox.on("input", (e) => {
			let query = e.target.value;

			if (query.length < 3 || !query.length) return;

			// Populate recent search chips
			me.setRecentSearches(query);

			// Fetch and populate product results
			frappe.call({
				method: "erpnext.templates.pages.product_search.search",
				args: {
					query: query
				},
				callback: (data) => {
					me.populateResults(data);
				}
			});

			// Populate categories
			if (me.category_container) {
				frappe.call({
					method: "erpnext.templates.pages.product_search.get_category_suggestions",
					args: {
						query: query
					},
					callback: (data) => {
						me.populateCategoriesList(data)
					}
				});
			}

			this.search_dropdown.removeClass("hidden");
		});
	}

	setupSearchResultContainer() {
		this.search_dropdown = this.search_area.append(`
			<div class="overflow-hidden shadow dropdown-menu w-100 hidden"
				id="search-results-container"
				aria-labelledby="dropdownMenuSearch"
				style="display: flex;">
			</div>
		`).find("#search-results-container");
	}

	setupProductsContainer() {
		let $products_section = this.search_dropdown.append(`
			<div class="col-7 mr-2 mt-1"
				id="product-results"
				style="border-right: 1px solid var(--gray-200);">
			</div>
		`).find("#product-results");

		this.products_container = $products_section.append(`
			<div id="product-scroll" style="overflow: scroll; max-height: 300px">
				<div class="mt-6 w-100 text-muted" style="font-weight: 400; text-align: center;">
					${ __("Type something ...") }
				</div>
			</div>
		`).find("#product-scroll");
	}

	setupCategoryRecentsContainer() {
		let $category_recents_section = $("#search-results-container").append(`
			<div id="category-recents-container"
				class="col-5 mt-2 h-100"
				style="margin-left: -15px;">
			</div>
		`).find("#category-recents-container");

		this.category_container = $category_recents_section.append(`
			<div class="category-container">
				<div class="mb-2"
					style="border-bottom: 1px solid var(--gray-200);">
					${ __("Categories") }
				</div>
				<div class="categories">
					<span class="text-muted" style="font-weight: 400;"> ${ __('No results') } <span>
				</div>
			</div>
		`).find(".categories");

		let $recents_section = $("#category-recents-container").append(`
			<div class="mb-2 mt-4 recent-searches">
				<div style="border-bottom: 1px solid var(--gray-200);">
					${ __("Recent") }
				</div>
			</div>
		`).find(".recent-searches");

		this.recents_container = $recents_section.append(`
			<div id="recent-chips" style="padding: 1rem 0;">
			</div>
		`).find("#recent-chips");
	}

	getRecentSearches() {
		return JSON.parse(localStorage.getItem("recent_searches") || "[]");
	}

	attachEventListenersToChips() {
		let me  = this;
		const chips = $(".recent-chip");
		window.chips = chips;

		for (let chip of chips) {
			chip.addEventListener("click", () => {
				me.searchBox[0].value = chip.innerText;

				// Start search with `recent query`
				me.searchBox.trigger("input");
				me.searchBox.focus();
			});
		}
	}

	setRecentSearches(query) {
		let recents = this.getRecentSearches();
		if (recents.length >= this.MAX_RECENT_SEARCHES) {
			// Remove the `first` query
			recents.splice(0, 1);
		}

		if (recents.indexOf(query) >= 0) {
			return;
		}

		recents.push(query);
		localStorage.setItem("recent_searches", JSON.stringify(recents));

		this.populateRecentSearches();
	}

	populateRecentSearches() {
		let recents = this.getRecentSearches();

		if (!recents.length) {
			return;
		}

		let html = "";
		recents.forEach((key) => {
			html += `<button class="btn btn-sm recent-chip mr-1 mb-2">${ key }</button>`;
		});

		this.recents_container.html(html);
		this.attachEventListenersToChips();
	}

	populateResults(data) {
		if (data.message.results.length === 0) {
			this.products_container.html('No results');
			return;
		}

		let html = "";
		let search_results = data.message.results;

		search_results.forEach((res) => {
			html += `
				<div class="dropdown-item" style="display: flex;">
					<img class="item-thumb col-2" src=${res.thumbnail || 'img/placeholder.png'} />
					<div class="col-9" style="white-space: normal;">
						<a href="/${res.route}">${res.web_item_name}</a><br>
						<span class="brand-line">${res.brand ? "by " + res.brand : ""}</span>
					</div>
				</div>
			`;
		});

		this.products_container.html(html);
	}

	populateCategoriesList(data) {
		if (data.message.results.length === 0) {
			let empty_html = `
				<span class="text-muted" style="font-weight: 400;">
					${__('No results')}
				</span>
			`;
			this.category_container.html(empty_html);
			return;
		}

		let html = ""
		let search_results = data.message.results
		search_results.forEach((category) => {
			html += `
				<div class="mb-2" style="font-weight: 400;">
					<a href="/${category.route}">${category.name}</a>
				</div>
			`;
		})

		this.category_container.html(html);
	}
}