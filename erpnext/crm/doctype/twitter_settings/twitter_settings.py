# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import requests
from requests_oauthlib import OAuth1
from frappe.utils.file_manager import get_file, get_file_path
import os
import mimetypes

MEDIA_ENDPOINT_URL = "https://upload.twitter.com/1.1/media/upload.json"

class TwitterSettings(Document):
	@frappe.whitelist()
	def get_authorize_url(self):
		callback_uri = "{0}/?cmd=erpnext.crm.doctype.twitter_settings.twitter_settings.callback".format(frappe.utils.get_url())
		consumer_secret = self.get_password(fieldname="consumer_secret")
		oauth = OAuth1(client_key=self.consumer_key, client_secret=consumer_secret, callback_uri=callback_uri)
		try:
			r = requests.post("https://api.twitter.com/oauth/request_token", auth=oauth)
		except Exception as e:
			frappe.throw(e)
			return
		if r.status_code == 200:
			from urllib.parse import parse_qs
			response = parse_qs(r.content.decode())
			response = frappe._dict(response)
			self.oauth_token = response.get("oauth_token")[0]
			self.oauth_secret = response.get("oauth_token_secret")[0]
			self.save()
			return "https://api.twitter.com/oauth/authorize?oauth_token={0}".format(self.oauth_token)
		else:
			return frappe.msgprint(r.status_code)
	
	def get_access_token(self):
		url = "https://api.twitter.com/oauth/access_token"
		consumer_secret = self.get_password(fieldname="consumer_secret")
		oauth = OAuth1(client_key=self.consumer_key, client_secret=consumer_secret,resource_owner_key= self.oauth_token, verifier=self.oauth_verifier)

		try:
			r = requests.post(url, auth=oauth)
		except Exception:
			frappe.throw(e)

		if r.status_code == 200:
			from urllib.parse import parse_qs
			response = parse_qs(r.content.decode())
			response = frappe._dict(response)
			self.oauth_token = response.get("oauth_token")[0]
			self.oauth_secret = response.get("oauth_token_secret")[0]
			self.account_name = response.get("screen_name")[0]
			self.save()
			
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = "/desk#Form/{0}".format(quote("Twitter Settings"))

			frappe.msgprint(_("Twitter Integration has been configured."))
		else:
			frappe.throw("Something Went Wrong. Please make sure your Consumer Key and Consumer Secret are correct")

	def post(self, text, media=None):
		if not media:
			return self.send_tweet(text)

		if media:
			media_id = self.upload_image(media)
			return self.send_tweet(text, media_id)
	
	def upload_image(self, media):
		media = get_file_path(media)
		total_bytes = os.path.getsize(media)

		if total_bytes > 5242880:
			frappe.throw("Image is too large")
			return
		
		request_data = {
			"command": "INIT",
			"media_type": mimetypes.guess_type(media),
			"total_bytes": total_bytes,
			"media_category": "tweet_image"
		}
		oauth = self.get_oauth()
		req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, auth=oauth)
		media_id = req.json()["media_id"]
		segment_id = 0
		bytes_sent = 0
		image = open(media,"rb")

		while bytes_sent < total_bytes:
			request_data = {
				"command": "APPEND",
				"media_id": media_id,
				"segment_index": segment_id
			}

			chunk = image.read(4*1024*1024)
			files = {
				"media": chunk
			}

			req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, files=files, auth=self.get_oauth())

			if req.status_code < 200 or req.status_code >299:
				print("ERROR UPLOADING FILE:" + str(req.status_code) + "BODY" + req.text)
				continue

			segment_id += 1
			bytes_sent = image.tell()
		
		request_data = {
			"command": "FINALIZE",
			"media_id": media_id
		}

		req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, auth=self.get_oauth())
		processing_info = req.json().get("processing_info", None)

		
		while processing_info and processing_info["state"] not in ["failed", "succeeded"]:
			check_after_secs = self.processing_info["check_after_secs"]
			time.sleep(check_after_secs)

			request_params = {
				"command": "STATUS",
				"media_id": self.media_id
			}

			req = requests.get(url=MEDIA_ENDPOINT_URL, params=request_params, auth=oauth)

			processing_info = req.json().get("processing_info", None)

		if not processing_info:
			return media_id
		state = processing_info["state"]
		if state == u"succeeded":
			return media_id

		if state == u"failed":
			return None


	def get_oauth(self):
		if self.oauth_token and self.oauth_secret:
			return  OAuth1(self.consumer_key, client_secret=self.get_password(fieldname="consumer_secret"), resource_owner_key=self.oauth_token, resource_owner_secret=self.get_password(fieldname="oauth_secret"))


	def send_tweet(self, text, media_id=None):
		from urllib.parse import urlencode
		url = "https://api.twitter.com/1.1/statuses/update.json"
		oauth = self.get_oauth()
		params = {
			"status": text,
			"media_ids": media_id
		}
		try :
			r = requests.post(url, auth=oauth, params=params)
			r.raise_for_status()
		except Exception as e:
			frappe.throw(e)
		return r.json()["id_str"]

@frappe.whitelist()
def callback(oauth_token, oauth_verifier):
	twitter_settings = frappe.get_single("Twitter Settings")
	twitter_settings.oauth_token = oauth_token
	twitter_settings.oauth_verifier = oauth_verifier
	twitter_settings.save()
	twitter_settings.get_access_token()
	# Callback will be a get request
	frappe.db.commit()