// used in documenation site built via document generator

$(function() {
	if(hljs) {
		$('pre code').each(function(i, block) {
			hljs.highlightBlock(block);
		});
	}

	// search
	$('.sidebar-navbar-items .octicon-search, .navbar .octicon-search').parent().on("click", function() {
		var modal = frappe.get_modal("Search",
		'<p><input class="search-input form-control" type="text" placeholder="Search text..." tabindex="1"></p>\
		<p><a class="btn btn-sm btn-default btn-search" href="#" target="_blank" tabindex="2">Search via Google</a></p>');
		modal.find(".search-input").on("keyup", function(e) {
			if(e.which===13) {
				modal.find(".btn-search").trigger("click");
			}
			if(e.which===9) {
				e.preventDefault();
				modal.find(".btn-search").focus();
				return false;
			}
			var text = $(this).val();
			modal.find(".btn-search").attr("href", "https://google.com/search?q="
				+ text + "+site:" + (window.docs_base_url || ""));
		});
		modal.modal("show");
		return false;
	});

});

frappe = {
	get_modal: function(title, body_html) {
		var modal = $('<div class="modal" style="overflow: auto;" tabindex="-1">\
			<div class="modal-dialog">\
				<div class="modal-content">\
					<div class="modal-header">\
						<a type="button" class="close"\
							data-dismiss="modal" aria-hidden="true">&times;</a>\
						<h4 class="modal-title">'+title+'</h4>\
					</div>\
					<div class="modal-body ui-front">'+body_html+'\
					</div>\
				</div>\
			</div>\
			</div>').appendTo(document.body);

		return modal;
	},
}
