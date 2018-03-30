# Print Format

Print Formats are the layouts that are generated when you want to Print or
Email a transaction like a Sales Invoice. There are two types of Print
Formats,

  * The auto-generated “Standard” Print Format: This type of format follows the same layout as the form and is generated automatically by ERPNext.
  * Based on the Print Format document. There are templates in HTML that will be rendered with data.

ERPNext comes with a number of pre-defined templates in three styles: Modern,
Classic and Standard.

You can modify the templates or create your own. Editing
ERPNext templates is not allowed because they may be over-written in an
upcoming release.

To create your own versions, open an existing template from:

`Setup > Printing > Print Formats`

<img alt="Print Format" class="screenshot" src="{{docs_base_url}}/assets/img/customize/print-format.png">

Select the type of Print Format you want to edit and click on the “Copy”
button on the right column. A new Print Format will open up with “Is Standard”
set as “No” and you can edit the Print Format.

Editing a Print Format is a long discussion and you will have to know a bit of
HTML, CSS, Python to learn this. For help, please post on our forum.

Print Formats are rendered on the server side using the [Jinja Templating Language](http://jinja.pocoo.org/docs/templates/). All forms have access to the doc object which contains information about the document that is being formatted. You can also access common utilities via the frappe module.

For styling, the [Bootstrap CSS Framework](http://getbootstrap.com/) is provided and you can enjoy the full range of classes.

> Note: Pre-printed stationary is usually not a good idea because your Prints
will look incomplete (inconsistent) when you send them by mail.

#### References

1. [Jinja Templating Language: Reference](http://jinja.pocoo.org/docs/templates/)
2. [Bootstrap CSS Framework](http://getbootstrap.com/)

#### Print Settings

To edit / update your print and PDF settings, go to:

`Setup > Printing and Branding > Print Settings`

<img alt="Print Format" class="screenshot" src="{{docs_base_url}}/assets/img/customize/print-settings.png">

#### Example

		{% raw %}<h3>{{ doc.select_print_heading or "Invoice" }}</h3>
		<div class="row">
			<div class="col-md-3 text-right">Customer Name</div>
			<div class="col-md-9">{{ doc.customer_name }}</div>
		</div>
		<div class="row">
			<div class="col-md-3 text-right">Date</div>
			<div class="col-md-9">{{ doc.get_formatted("invoice_date") }}</div>
		</div>
		<table class="table table-bordered">
			<tbody>
				<tr>
					<th>Sr</th>
					<th>Item Name</th>
					<th>Description</th>
					<th class="text-right">Qty</th>
					<th class="text-right">Rate</th>
					<th class="text-right">Amount</th>
				</tr>
				{%- for row in doc.items -%}
				<tr>
					<td style="width: 3%;">{{ row.idx }}</td>
					<td style="width: 20%;">
						{{ row.item_name }}
						{% if row.item_code != row.item_name -%}
						<br>Item Code: {{ row.item_code}}
						{%- endif %}
					</td>
					<td style="width: 37%;">
						<div style="border: 0px;">{{ row.description }}</div></td>
					<td style="width: 10%; text-align: right;">{{ row.qty }} {{ row.uom or row.stock_uom }}</td>
					<td style="width: 15%; text-align: right;">{{
						row.get_formatted("rate", doc) }}</td>
					<td style="width: 15%; text-align: right;">{{
						row.get_formatted("amount", doc) }}</td>
				</tr>
				{%- endfor -%}
			</tbody>
		</table>{% endraw %}

#### Notes

1. To get date and currency formatted values use, `doc.get_formatted("fieldname")`
1. For translatable strings, us `{{ _("This string is translated") }}`

#### Footers

Many times you may want to have a standard footer for your prints with your
address and contact information. Unfortunately due to the limited print
support in HTML pages, it is not possible unless you get it scripted. Either
you can use pre-printed stationary or add this information in your header.

{next}
