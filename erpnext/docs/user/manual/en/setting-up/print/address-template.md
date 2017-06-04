# Address Template

Each region has its own way of defining Addresses. To manage multiple address formats for your Documents (like Quotation, Purchase Invoice etc.), you can create country-wise **Address Templates**.

> Setup > Printing and Branding > Address Template

A default Address Template is created when you setup the system. You can either edit or update it or create a new template.

One template is default and will apply to all countries that do not have an specific template.

#### Template

The templating engine is based on HTML and the [Jinja Templating](http://jinja.pocoo.org/docs/templates/) system and all the fields (including Custom Fields) will be available for creating the template.

Here is the default template:

	{% raw %}{{ address_line1 }}<br>
	{% if address_line2 %}{{ address_line2 }}<br>{% endif -%}
	{{ city }}<br>
	{% if state %}{{ state }}<br>{% endif -%}
	{% if pincode %}PIN:  {{ pincode }}<br>{% endif -%}
	{{ country }}<br>
	{% if phone %}Phone: {{ phone }}<br>{% endif -%}
	{% if fax %}Fax: {{ fax }}<br>{% endif -%}
	{% if email_id %}Email: {{ email_id }}<br>{% endif -%}{% endraw %}

### Example

<img class="screenshot" alt="Print Heading" src="{{docs_base_url}}/assets/img/setup/print/address-format.png">

{next}
