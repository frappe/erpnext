# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, os, tweepy, json
from frappe import _
from frappe.model.document import Document
from frappe.utils.file_manager import get_file_path
from frappe.utils import get_url_to_form, get_link_to_form
from tweepy.error import TweepError

class TwitterSettings(Document):
	def get_authorize_url(self):
		callback_url = "{0}/api/method/erpnext.crm.doctype.twitter_settings.twitter_settings.callback?".format(frappe.utils.get_url())
		auth = tweepy.OAuthHandler(self.consumer_key, self.get_password(fieldname="consumer_secret"), callback_url)
		try:
			redirect_url = auth.get_authorization_url()
			return redirect_url
		except tweepy.TweepError as e:
			frappe.msgprint(_("Error! Failed to get request token."))
			frappe.throw(_('Invalid {0} or {1}').format(frappe.bold("Consumer Key"), frappe.bold("Consumer Secret Key")))

	
	def get_access_token(self, oauth_token, oauth_verifier):
		auth = tweepy.OAuthHandler(self.consumer_key, self.get_password(fieldname="consumer_secret"))
		auth.request_token = { 
			'oauth_token' : oauth_token,
			'oauth_token_secret' : oauth_verifier 
		}

		try:
			auth.get_access_token(oauth_verifier)
			api = self.get_api(auth.access_token, auth.access_token_secret)
			user = api.me()
			profile_pic = (user._json["profile_image_url"]).replace("_normal","")

			frappe.db.set_value(self.doctype, self.name, {
				"access_token" : auth.access_token,
				"access_token_secret" : auth.access_token_secret,
				"account_name" : user._json["screen_name"],
				"profile_pic" : profile_pic,
				"session_status" : "Active"
			})

			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = get_url_to_form("Twitter Settings","Twitter Settings")
		except TweepError as e:
			frappe.msgprint(_("Error! Failed to get access token."))
			frappe.throw(_('Invalid Consumer Key or Consumer Secret Key'))

	def get_api(self, access_token, access_token_secret):
		# authentication of consumer key and secret 
		auth = tweepy.OAuthHandler(self.consumer_key, self.get_password(fieldname="consumer_secret")) 
		# authentication of access token and secret 
		auth.set_access_token(access_token, access_token_secret) 

		return tweepy.API(auth)

	def post(self, text, media=None):
		if not media:
			return self.send_tweet(text)

		if media:
			media_id = self.upload_image(media)
			return self.send_tweet(text, media_id)
	
	def upload_image(self, media):
		media = get_file_path(media)
		api = self.get_api(self.access_token, self.access_token_secret)
		media = api.media_upload(media)

		return media.media_id

	def send_tweet(self, text, media_id=None):
		api = self.get_api(self.access_token, self.access_token_secret)
		try:
			if media_id:
				response = api.update_status(status = text, media_ids = [media_id])
			else:
				response = api.update_status(status = text)

			return response

		except TweepError as e:
			content = json.loads(e.response.content)
			content = content["errors"][0]
			if e.response.status_code == 401:
				self.db_set("session_status", "Expired")
				frappe.db.commit()
			frappe.throw(content["message"],title="Twitter Error {0} {1}".format(e.response.status_code, e.response.reason))

@frappe.whitelist(allow_guest=True)
def callback(oauth_token = None, oauth_verifier = None):
	if oauth_token and oauth_verifier:
		twitter_settings = frappe.get_single("Twitter Settings")
		twitter_settings.get_access_token(oauth_token,oauth_verifier)
		frappe.db.commit()
	else:
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = get_url_to_form("Twitter Settings","Twitter Settings")
