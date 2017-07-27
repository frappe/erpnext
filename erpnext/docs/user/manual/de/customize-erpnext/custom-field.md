# Benutzerdefiniertes Feld
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Die Funktion "Benutzerdefiniertes Feld" erlaubt es Ihnen Felder in bestehenden Vorlagen und Transaktionen nach Ihren Wünschen zu gestalten. Wenn Sie ein benutzerdefiniertes Feld einfügen, können Sie seine Eigenschaften angeben:

* Feldname
* Feldtyp
* Erforderlich/nicht erforderlich
* Einfügen nach Feld

Um ein benutzerdefiniertes Feld hinzuzufügen, gehen Sie zu:

> Einstellungen > Anpassen > Benutzerdefiniertes Feld > Neu

Sie können ein neues benutzerdefiniertes Feld auch über das [Werkzeug zum Anpassen von Feldern]({{docs_base_url}}/user/manual/de/customize-erpnext/customize-form) einfügen.

In einem benutzerdefinierten Formular finden Sie für jedes Feld die Plus(+)-Option. Wenn Sie auf dieses Symbol klicken, wird eine neue Zeile oberhalb dieses Feldes eingefügt. Sie können die Einstellungen für Ihr Feld in der neu eingefügten leeren Zeile eingeben.

<img alt="Formular anpassen - benutzerdefiniertes Feld" class="screenshot" src="{{docs_base_url}}/assets/img/customize/custom-field-2.gif">

Im Folgenden sind die Schritte aufgeführt, wie man ein benutzerdefiniertes Feld in ein bestehendes Formular einfügt.

### Neues benutzerdefiniertes Feld in Formular / Zeile in einem benutzerdefinierten Formular

Wie bereits oben angesprochen, können Sie ein benutzerdefiniertes Feld über das Formular zum benutzerdefinierten Feld oder über ein benutzerdefiniertes Formular einfügen.

### Dokument/Formular auswählen

Wählen Sie die Transaktion oder die Vorlage, in die sie ein benutzerdefiniertes Feld einfügen wollen. Nehmen wir an, dass Sie ein benutzerdefiniertes Verknüpfungsfeld in ein Angebotsformular einfügen wollen; das Dokument soll "Angebot" heißen.

<img alt="Select Document Type" class="screenshot" src="{{docs_base_url}}/assets/img/customize/custom-field-1.gif">

### Feldbezeichnung einstellen

Die Bezeichnung des benutzerdefinierten Feldes wird basierend auf seinem Namen eingestellt. Wenn Sie ein benutzerdefiniertes Feld mit einem bestimmten Namen erstellen wollen, aber mit einer sich davon unterscheidenden Bezeichnung, dann sollten Sie erst die Bezeichnung angeben, da Sie den Feldnamen noch einstellen wollen. Nach dem Speichern des benutzerdefinierten Feldes können Sie die Feldbezeichnung wieder ändern.

<img alt="Select Document Type" class="screenshot" src="{{docs_base_url}}/assets/img/customize/custom-field-2.gif">

### Einstellen, nach welchem Element eingefügt werden soll ("Einfügen nach")

Diese Auswahl enthält alle bereits existierenden Felder des ausgewählten Formulars/des DocTypes. Ihr benutzerdefiniertes Feld wird nach dem Feld eingefügt, das Sie unter "Einfügen nach" auswählen.

<img alt="Select Document Type" class="screenshot" src="{{docs_base_url}}/assets/img/customize/custom-field-3.png">

### Feldtyp auswählen

Klicken Sie hier um weitere Informationen über Feldtypen, die Sie bei einem benutzerdefinierten Feld auswählen können, zu erhalten.

<img alt="Select Document Type" class="screenshot" src="{{docs_base_url}}/assets/img/customize/custom-field-4.png">

### Optionen einstellen

Wenn Sie ein Verknüpfungsfeld erstellen,dann wird der Name des DocType, mit dem dieses Feld verknüpft werden soll, in das Feld "Optionen" eingefügt. Klicken Sie [hier]({{docs_base_url}}/user/manual/en/customize-erpnext/articles/creating-custom-link-field) um weitere Informationen darüber zu erhalten, wie man benutzerdefinierte Verknüpfungsfelder erstellt.

<img alt="Select Document Type" class="screenshot" src="{{docs_base_url}}/assets/img/customize/custom-field-5.png">

Wenn der Feldtyp als Auswahlfeld (Drop Down-Feld) angegeben ist, dann sollten alle möglichen Ergebnisse für dieses Feld im Optionen-Feld aufgelistet werden. Die möglichen Ergebnisse sollten alle in einer eigenen Zeile stehen.

Bei anderen Feldtypen, wie Daten, Datum, Währung usw. lassen Sie das Optionen-Feld leer.

### Weitere Eigenschaften

Sie können weitere Eigenschaften auswählen wie:

1. Ist Pflichtfeld: Ist das Feld zwingend erforderlich oder nicht?
2. Beim Drucken verbergen: Soll dieses Feld beim Ausdruck sichtbar sein oder nicht?
3. Feldbeschreibung: Hier steht eine kurze Beschreibung des Feldes die gleich unter dem Feld erscheint.
4. Standardwert: Der Wert in diesem Feld wird automatisch aktualisiert.
5. Schreibgeschützt: Wenn diese Option aktiviert ist, kann das benutzerdefinierte Feld nicht geändert werden.
6. Beim Übertragen zulassen: Wenn diese Option ausgewählt wird, ist es erlaubt den Wert des Feldes zu ändern, wenn er in einer Transaktion übertragen wird.

<img alt="Select Document Type" class="screenshot" src="{{docs_base_url}}/assets/img/customize/custom-field-6.png">

### Benutzerdefiniertes Feld löschen

Wenn er die Berechtigung hat, kann ein Benutzer ein benutzerdefiniertes Feld löschen. Zum Beisiel dann, wenn es standardmäßig gelöscht wird, weil ein anderes benutzerdefiniertes Feld mit gleichem Namen hinzugefügt wurde. Dann sollten Sie das neue Feld automatisch dort angeordnet sehen, wo das alte Feld gelöscht wurde.

{next}
