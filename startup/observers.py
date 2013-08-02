# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

observer_map = {
	"*:on_update": "home.update_feed",
	"*:on_submit": "home.update_feed",
	"Stock Entry:on_submit": "stock.doctype.material_request.material_request.update_completed_qty",
	"Stock Entry:on_cancel": "stock.doctype.material_request.material_request.update_completed_qty",
}