# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from home import update_feed
from core.doctype.notification_count.notification_count import clear_doctype_notifications
from stock.doctype.material_request.material_request import update_completed_qty

def on_method(bean, method):
	if method in ("on_update", "on_submit"):
		update_feed(bean.controller, method)
	
	if method in ("on_update", "on_cancel", "on_trash"):
		clear_doctype_notifications(bean.controller, method)

	if bean.doc.doctype=="Stock Entry" and method in ("on_submit", "on_cancel"):
		update_completed_qty(bean.controller, method)