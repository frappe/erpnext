pscript.onload_unsubscribe = function(wrapper) {
	var email = window.location.hash.split('/').splice(-1);
	$(wrapper).find('input[name="unsubscribe"]').val(email)
	
	$('#btn-unsubscribe').click(function() {
		var email = $(wrapper).find('input[name="unsubscribe"]').val();
		if(email) {
			var btn = this;
			wn.call({
				module:'website',
				page:'unsubscribe',
				method:'unsubscribe',
				args:email,
				btn: this,
				callback: function() {
					$(wrapper).find('input[name="unsubscribe"]').val('');
				}
			});
		}
	});
}