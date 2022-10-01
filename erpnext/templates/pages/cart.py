# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from erpnext.e_commerce.shopping_cart.cart import get_cart_quotation

no_cache = 1


def get_context(context):
	context.body_class = "product-page"
	context.update(get_cart_quotation())
