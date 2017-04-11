# Adressvorlagen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Jede Region hat Ihre eigene Art und Weise, wie eine Adresse aussieht. Um mehrere verschiedene Adressformate für Ihre Dokumente (wie Angebot, Lieferantenauftrag, etc.) zu verwalten, können Sie landesspezifische **Adressvorlagen** erstellen.

> Einstellungen > Druck > Adressvorlage

Wenn Sie das System einrichten, wird eine Standard-Adressvorlage erstellt. Sie können diese sowohl bearbeiten als auch aktualisieren um eine neue Vorlage zu erstellen.

Eine Vorlage ist die Standardvorlage und wird für alle Länder verwendet, für die keine eigene Vorlage gilt.

#### Vorlage

Das Programm zum Erstellen von Vorlagen basiert auf HTML und [Jinja Templating](http://jinja.pocoo.org/docs/templates/) und alle Felder (auch die benutzerdefinierten) sind verfügbar um eine Vorlage zu erstellen.

Hier sehen Sie die Standardvorlage:

	{% raw %}{{ address_line1 }}<br>
	{% if address_line2 %}{{ address_line2 }}<br>{% endif -%}
	{{ city }}<br>
	{% if state %}{{ state }}<br>{% endif -%}
	{% if pincode %}PIN:  {{ pincode }}<br>{% endif -%}
	{{ country }}<br>
	{% if phone %}Phone: {{ phone }}<br>{% endif -%}
	{% if fax %}Fax: {{ fax }}<br>{% endif -%}
	{% if email_id %}Email: {{ email_id }}<br>{% endif -%}{% endraw %}


### Beispiel

<img class="screenshot" alt="Adressvorlage" src="{{docs_base_url}}/assets/img/setup/print/address-format.png">

{next}
