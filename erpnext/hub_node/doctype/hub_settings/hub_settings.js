frappe.ui.form.on("Hub Settings", {
	refresh: function(frm) {
		frm.add_custom_button(__('Logs'),
			() => frappe.set_route('List', 'Data Migration Run', {
				data_migration_plan: 'Hub Sync'
			}));

		frm.trigger("enabled");

		if (frm.doc.enabled) {
			frm.add_custom_button(__('Sync'),
				() => frm.call('sync'));
		}
	},
	onload: function(frm) {
		let token = frappe.urllib.get_arg("access_token");
		if(token) {
			let email = frm.get_field("user");
			console.log('token', frappe.urllib.get_arg("access_token"));

			get_user_details(frm, token, email);
			let row = frappe.model.add_child(frm.doc, "Hub Users", "users");
			row.user = frappe.session.user;
		}

		if(!frm.doc.country) {
			frm.set_value("country", frappe.defaults.get_default("Country"));
		}
		if(!frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("Company"));
		}
		if(!frm.doc.user) {
			frm.set_value("user", frappe.session.user);
		}
	},
	onload_post_render: function(frm) {
		if(frm.get_field("unregister_from_hub").$input)
			frm.get_field("unregister_from_hub").$input.addClass("btn-danger");
	},
	on_update: function(frm) {
	},
	enabled: function(frm) {
		if(!frm.doc.enabled) {
			frm.trigger("set_enable_hub_primary_button");
		} else {
			frm.page.set_primary_action(__("Save Settings"), () => {
				frm.save();
			});
		}
	},

	hub_user_email: function(frm) {
		if(frm.doc.hub_user_email){
			frm.set_value("hub_user_name", frappe.user.full_name(frm.doc.hub_user_email));
		}
	},

	set_enable_hub_primary_button: (frm) => {
		frm.page.set_primary_action(__("Enable Hub"), () => {
			if(frappe.session.user === "Administrator") {
				frappe.msgprint(__("Please login as another user."))
			} else {
				// frappe.verify_password(() => {

				// } );

				frm.trigger("call_pre_reg");
				// frm.trigger("call_register");

			}
		});
	},

	call_pre_reg: (frm) => {
		this.frm.call({
			doc: this.frm.doc,
			method: "pre_reg",
			args: {},
			freeze: true,
			callback: function(r) {
				console.log(r.message);
				authorize(frm, r.message.client_id, r.message.redirect_uri);
			},
			onerror: function() {
				frappe.msgprint(__("Wrong Password"));
				frm.set_value("enabled", 0);
			}
		});
	},

	call_register: (frm) => {
		this.frm.call({
			doc: this.frm.doc,
			method: "register",
			args: {},
			freeze: true,
			callback: function(r) {},
			onerror: function() {
				frappe.msgprint(__("Wrong Password"));
				frm.set_value("enabled", 0);
			}
		});
	},

	unregister_from_hub: (frm) => {
		frappe.verify_password(() => {
			var d = frappe.confirm(__('Are you sure you want to unregister?'), () => {
				frm.call('unregister');
			}, () => {}, __('Confirm Action'));
			d.get_primary_btn().addClass("btn-danger");
		});
	},
});

// let hub_url = 'https://hubmarket.org'
let hub_url = 'http://159.89.175.122'
// let hub_url = 'http://erpnext.hub:8000'

function authorize(frm, client_id, redirect_uri) {

    // queryStringData is details of OAuth Client (Implicit Grant) on Custom App
	var queryStringData = {
		response_type : "token",
		client_id : client_id,
        redirect_uri : redirect_uri
	}

    // Get current raw route and build url
    const route = "/desk#" + frappe.get_raw_route_str();
    localStorage.removeItem("route");  // Clear previously set route if any
	localStorage.setItem("route", route);

	// Go authorize!
	let api_route = "/api/method/frappe.integrations.oauth2.authorize?";
	let url = hub_url + api_route + $.param(queryStringData);
	window.location.replace(url, 'test');
}

function get_user_details(frm, token, email) {
	console.log('user_details');
    var route = localStorage.getItem("route");
    if (token && route) {
        // Clean up access token from route
		frappe.set_route(frappe.get_route().join("/"))

        // query protected resource e.g. Hub Items with token
        var call = {
            "async": true,
            "crossDomain": true,
            "url": hub_url + "/api/resource/User",
			"method": "GET",
			"data": {
				// "email": email,
				"fields": '["name", "first_name", "language"]',
				"limit_page_length": 1
			},
            "headers": {
                "authorization": "Bearer " + token,
                "content-type": "application/x-www-form-urlencoded"
            }
		}
        $.ajax(call).done(function (response) {
			// display openid profile
			console.log('response', response);

			let data = response.data[0];
			frm.set_value("enabled", 1);
			frm.set_value("hub_username", data.first_name);
			frm.set_value("hub_user_status", "Starter");
			frm.set_value("language", data.language);
			frm.save();

            // clear route from localStorage
            localStorage.removeItem("route");
        });
    }
}
