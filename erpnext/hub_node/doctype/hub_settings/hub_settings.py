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

hub_url = "http://erpnext.hub:8000"
# hub_url = "http://hub.erpnext.org"

class HubSettings(Document):
	config_args = ['enabled']
	profile_args = ['email', 'hub_user_name', 'country', 'company']  # also 'public_key_pem'
	only_in_code = ['private_key']
	seller_args = ['publish', 'seller_city', 'seller_website', 'seller_description']
	publishing_args = ['publish_pricing', 'selling_price_list', 'publish_availability', 'warehouse']
	personal_args = ['hub_public_key_pem']

	base_fields_for_items = ["name", "item_code", "item_name", "description", "image", "item_group",
		 "modified"] #"price", "stock_uom", "stock_qty"

	def reset_current_on_save_flags(self):
		self.item_fields_to_add = []
		self.item_fields_to_remove = []
		self.publishing_changed = {
			"publish": 0,
			"publish_pricing": 0,
			"publish_availability": 0
		}

	def validate(self):
		self.before_update = frappe.get_doc('Hub Settings', self.name)
		self.reset_current_on_save_flags()
		self.update_settings_changes()
		if (self.publishing_changed["publish_pricing"] or
			self.publishing_changed["publish_availability"]):
			self.update_fields()

	def on_update(self):
		if not self.access_token:
			if self.enabled:
				frappe.throw(_("Enabled without access_token"))
			return

		# If just registered
		if self.enabled != self.before_update.enabled and self.enabled == 1:
			return

		self.update_hub()
		self.update_item_fields_state()

	def update_settings_changes(self):
		# Pick publishing changes
		for setting in self.publishing_changed.keys():
			if self.get(setting) != self.before_update.get(setting):
				self.publishing_changed[setting] = 1

	def update_fields(self):
		if self.publishing_changed["publish_pricing"]:
			# TODO: pricing
			fields = ["", ""]
			if self.publish_pricing:
				self.item_fields_to_add += fields
			else:
				self.item_fields_to_remove += fields
		if self.publishing_changed["publish_availability"]:
			# fields = ["stock_uom", "stock_qty"]
			fields = ["stock_uom"]
			if self.publish_availability:
				self.item_fields_to_add += fields
			else:
				self.item_fields_to_remove += fields

	def update_item_fields_state(self):
		fields_step_1 = json.loads(self.current_item_fields)
		fields_step_1 += self.item_fields_to_add
		fields_step_2 = [f for f in set(fields_step_1) if f not in self.item_fields_to_remove]
		self.current_item_fields = json.dumps(fields_step_2)

	def update_hub(self):
		# Updating profile call
		response_msg = call_hub_api_now('update_user_details',
			data=self.get_args(self.profile_args + self.seller_args))

		self.update_publishing()

	def update_publishing(self):
		if self.publishing_changed["publish"]:
			if self.publish:
				fields = json.loads(self.current_item_fields)
				fields += self.item_fields_to_add
				self.current_item_fields = json.dumps(fields)
				# [batch and enqueue] publishing call with all field values for all items (just like now)
				self.publish_all_set_items()
			else:
				self.reset_publishing_settings()
				# unpublishing call
				self.unpublish_all_items()
		else:
			if self.item_fields_to_add:
				# [batch and enqueue] adding call with name and these field values for all items
				self.add_item_fields_at_hub()
			if self.item_fields_to_remove:
				# removing call with that list
				self.remove_item_fields_at_hub()

	def publish_all_set_items(self, verbose=True):
		"""Publish items hub.erpnext.org"""
		# A way to set 'publish in hub' for a bulk of items, if not all are by default, like
		self.publish_selling_items()

		fields = json.loads(self.current_item_fields)

		items = frappe.db.get_all("Item", fields=fields, filters={"publish_in_hub": 1})
		if not items:
			frappe.msgprint(_("No published items found."))
			return

		for item in items:
			item.modified = get_datetime_str(item.modified)
			if item.image:
				item.image = expand_relative_urls(item.image)
		item_list = frappe.db.sql_list("select name from tabItem where publish_in_hub=1")

		response_msg = call_hub_api_now('update_items',
			data={
			"items_to_update": json.dumps(items),
			"item_list": json.dumps(item_list),
			"item_fields": fields
		})
		self.last_sync_datetime = response_msg.get("last_sync_datetime")

		if verbose:
			frappe.msgprint(_("{0} Items synced".format(len(items))))

	def unpublish_all_items(self):
		"""Unpublish from hub.erpnext.org, delete items there"""
		response_msg = call_hub_api_now('unpublish_items')

	def add_item_fields_at_hub(self):
		items = frappe.db.get_all("Item", fields=["item_code"] + self.item_fields_to_add, filters={"publish_in_hub": 1})
		response_msg = call_hub_api_now('add_item_fields',
			data={
				"items_with_new_fields": json.dumps(items),
				"fields_to_add": self.item_fields_to_add
			}
		)

	def remove_item_fields_at_hub(self):
		response_msg = call_hub_api_now('remove_item_fields',
			data={"fields_to_remove": self.item_fields_to_remove})

	### Account
	def register(self):
		"""Register at hub.erpnext.org and exchange keys"""
		# if self.access_token or hasattr(self, 'private_key'):
		# 	return
		(self.private_key, self.public_key_pem) = generate_keys()
		response = requests.post(hub_url + "/api/method/hub.hub.api."+"register",
			data = { "args_data": json.dumps(self.get_args(
				self.config_args + self.profile_args + ['public_key_pem']
			))}
		)
		response.raise_for_status()
		response_msg = response.json().get("message")

		self.access_token = response_msg.get("access_token")
		self.hub_public_key = load_pem_public_key(	# An rsa.RSAPublicKey object
			str(response_msg.get("hub_public_key_pem")),
			backend=default_backend()
		)

		# Set start values
		self.current_item_fields = json.dumps(self.base_fields_for_items)
		self.last_sync_datetime = add_years(now(), -10)

	def unregister_from_hub(self):
		"""Unpublish, then delete transactions and user from there"""
		self.reset_publishing_settings()
		response_msg = call_hub_api_now('unregister')

	### Helpers
	def get_args(self, arg_list):
		args = {}
		for d in arg_list:
			args[d] = self.get(d)
		return args

	def reset_publishing_settings(self):
		self.publish = 0
		self.publish_pricing = 0
		self.publish_availability = 0
		self.current_item_fields = json.dumps(self.base_fields_for_items)


	def publish_selling_items(self):
		"""Set `publish_in_hub`=1 for all Sales Items"""
		for item in frappe.get_all("Item", fields=["name"],
			filters={ "publish_in_hub": 0, "is_sales_item": 1}):
			frappe.db.set_value("Item", item.name, "publish_in_hub", 1)


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
		response = requests.post(hub_url + "/api/method/hub.hub.api." + hub_decryption_method,
			data = {
				"access_token": self.access_token,
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

### Helpers
def call_hub_api_now(method, data = []):
	hub = frappe.get_single("Hub Settings")
	response = requests.post(hub_url + "/api/method/hub.hub.api." + "call_method",
		data = {
			"access_token": hub.access_token,
			"method": method,
			"message": json.dumps(data)
		}
	)
	response.raise_for_status()
	return response.json().get("message")

### Sender terminal
def make_message_queue_table():
	pass

def store_as_job_message(method, data):
	# encrypt data and store both params in message queue
	pass

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