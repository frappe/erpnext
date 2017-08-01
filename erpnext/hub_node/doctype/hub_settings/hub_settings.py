# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json, cryptography, os
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

from frappe.model.document import Document
from frappe.utils import cint, expand_relative_urls, fmt_money, flt, add_years, add_to_date, now, get_datetime, get_datetime_str
from frappe import _
from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item

class HubSettings(Document):
	# make a form with an enable hub button, that unhides profile section (mandatory fields)
	# which on submitting, unhides publish check, which unlocks the publish options

	hub_url = "http://erpnext.hub:8000"
	# hub_url = "http://hub.erpnext.org"

	config_args = ['enabled']
	profile_args = ['email', 'hub_user_name', 'company', 'country']  # also 'public_key_pem'
	only_in_code = ['private_key']
	seller_args = ['publish', 'seller_city', 'seller_website', 'seller_description',
		'publish_pricing', 'selling_price_list', 'publish_availability', 'warehouse']
	personal_args = ['hub_public_key_pem']

	item_fields = ["name", "item_code", "item_name", "description", "image", "item_group",
		"stock_uom", "modified", "price", "stock_qty"]

	def validate(self):
		# self.before_update = frappe.get_doc('Hub Settings', self.name)

		if self.enabled:
			if not self.password and not hasattr(self, 'private_key'):
				self.register() # get password
				self.last_sync_datetime = add_years(now(), -10)

	def on_update(self):
		self.update_hub()

	### Account methods
	def register(self):
		"""Register at hub.erpnext.org and exchange keys"""
		(self.private_key, self.public_key_pem) = generate_keys()

		response = requests.post(self.hub_url + "/api/method/hub.hub.api."+"register",
			data = { "args_data": json.dumps(self.get_args(self.config_args + self.profile_args + ['public_key_pem'])) })
		response.raise_for_status()
		response_msg = response.json().get("message")

		self.password = response_msg.get("password")
		# rsa.RSAPublicKey
		self.hub_public_key = load_pem_public_key(
			str(response_msg.get("hub_public_key_pem")),
			backend=default_backend()
		)

	def unregister(self):
		response_msg = self.call_hub_api_plaintext('unregister',
			data=self.get_args(self.profile_args + self.seller_args))

	def update_hub(self):
		response_msg = self.call_hub_api_plaintext('update_user_details',
			data=self.get_args(self.profile_args + self.seller_args))
		if self.publish:
			self.sync(False)

	def publish(self):
		"""Publish items hub.erpnext.org"""
		self.sync()

	def unpublish(self):
		"""Unpublish from hub.erpnext.org, delete items there"""
		response = requests.post(self.hub_url + "/api/method/hub.hub.api.unpublish", data={
			"password": self.password
		})
		response.raise_for_status()

	def sync(self, now = True, verbose=True):
		"""Sync items with hub.erpnext.org"""
		item_fields = ["name", "item_code", "item_name", "description", "image", "item_group", "stock_uom", "modified"]
		items = frappe.db.get_all("Item", fields=item_fields, filters={"publish_in_hub": 1, "modified": ['>', get_datetime(self.last_sync_datetime)]})
		if not items:
			frappe.msgprint(_("Items already synced"))
			return

		for item in items:
			item.modified = get_datetime_str(item.modified)
			if item.image:
				item.image = expand_relative_urls(item.image)
		item_list = frappe.db.sql_list("select name from tabItem where publish_in_hub=1")

		response_msg = self.call_hub_api_plaintext('sync',
			data={
			"items_to_update": json.dumps(items),
			"item_list": json.dumps(item_list)
		})
		self.last_sync_datetime = response_msg.get("last_sync_datetime")

		if verbose:
			frappe.msgprint(_("{0} Items synced".format(len(items))))

	def publish_selling_items(self):
		"""Set `publish_in_hub`=1 for all Sales Items"""
		# for item in frappe.get_all("Item", fields=["name"],
		# 	filters={ "publish_in_hub": 0, "is_sales_item": 1}):
		# 	frappe.db.set_value("Item", item.name, "publish_in_hub", 1)
		pass

	### Helpers
	def call_hub_api_plaintext(self, method, data):
		response = requests.post(self.hub_url + "/api/method/hub.hub.api." + "call_method",
			data = {
				"password": self.password,
				"method": method,
				"message": json.dumps(data)
			}
		)
		response.raise_for_status()
		return response.json().get("message")

	def call_hub_api(self, method, data):
		# Encryption
		payload = bytes(json.dumps(data))
		key = Fernet.generate_key()

		# Encrypt message
		f = Fernet(key)
		encrypted_payload = f.encrypt(payload)

		# Encrypt key
		encrypted_key = self.hub_public_key.encrypt(
			key,
			padding.OAEP(
				mgf=padding.MGF1(algorithm=hashes.SHA1()),
				algorithm=hashes.SHA1(),
				label=None
			)
		)

		# Sign key
		signature = self.private_key.sign(
			encrypted_key,
			padding.PSS(
				mgf=padding.MGF1(hashes.SHA256()),
				salt_length=padding.PSS.MAX_LENGTH
			),
			hashes.SHA256()
		)

		print type(encrypted_key)
		print type(encrypted_payload)
		print len(encrypted_key)

		# print unicode(encrypted_key, 'latin-1')
		# print encrypted_key.decode('unicode-escape')
		print len(encrypted_key.decode('latin-1'))
		print unicode(encrypted_key.decode('latin-1'))
		# print type(signature)

		hub_decryption_method = "decrypt_message_and_call_method"
		response = requests.post(self.hub_url + "/api/method/hub.hub.api." + hub_decryption_method,
			data = {
				"password": self.password,
				"method": method,
				# "signature": signature,
				"encrypted_key": unicode(encrypted_key.decode('latin-1')),
				"message": unicode(encrypted_payload.decode('latin-1')),
				# "encrypted_key": encrypted_key.decode('unicode-escape'),
				# "message": encrypted_payload.decode('unicode-escape')
			}
		)
		print "=============5=============="
		response.raise_for_status()
		return response.json().get("message")

	def get_args(self, arg_list):
		args = {}
		for d in arg_list:
			args[d] = self.get(d)
		return args

		# return {
		# 	"enabled": self.enabled,
		# 	"hub_user_name": self.hub_user_name,
		# 	"company": self.company,
		# 	"country": self.country,
		# 	"email": self.email,
		# 	"publish": self.publish,
		# 	"public_key_pem": self.pem_pub,
		# 	"seller_city": self.seller_city,
		# 	"seller_website": self.seller_website,
		# 	"seller_description": self.seller_description,
		# 	"publish_pricing": self.publish_pricing,
		# 	"selling_price_list": self.selling_price_list,
		# 	"publish_availability": self.publish_availability,
		# 	"warehouse": self.warehouse
		# }

	# def get_item_details(self, item):
	# 	item_code = item.item_code
	# 	template_item_code = frappe.db.get_value("Item", item_code, "variant_of")
	# 	# item = get_qty_in_stock(item, template_item_code, self.warehouse, self.last_sync_datetime)
	# 	# item = get_price(item, template_item_code, self.selling_price_list, self.company, self.last_sync_datetime)
	# 	return item

	def get_item_details(self, item):
		"Get stock and price info"
		pass


### Helpers
def generate_keys():
	"""Generate RSA public and private keys and write to files in site directory"""
	private_key = None
	public_key = None

	private_files = frappe.get_site_path('private', 'files')
	if os.path.exists(os.path.join(private_files, "hub_client_rsa")):
		with open(os.path.join(private_files, "hub_client_rsa"), "rb") as private_key_file, open("hub_client_rsa.pub", "rb") as public_key_file:
				private_key = serialization.load_pem_private_key(private_key_file.read(), password=None, backend=default_backend())
				public_key = private_key.public_key()

				pem_priv = private_key_file.read()
				pem_pub = public_key_file.read()
				return (public_key, private_key, pem_priv, pem_pub)

	private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
	public_key = private_key.public_key()
	# pem_priv = private_key.private_bytes(
	# 	encoding=serialization.Encoding.PEM,
	# 	format=serialization.PrivateFormat.TraditionalOpenSSL,
	# 	encryption_algorithm=serialization.NoEncryption()
	# )
	# with open(os.path.join(private_files, "hub_client_rsa"), 'w') as priv:
	# 	priv.write(pem_priv)

	pem_pub = public_key.public_bytes(
		encoding=serialization.Encoding.PEM,
		format=serialization.PublicFormat.SubjectPublicKeyInfo
	)
	with open(os.path.join(private_files, "hub_client_rsa.pub"), 'w') as pub:
		pub.write(pem_pub)

	return (private_key, pem_pub)