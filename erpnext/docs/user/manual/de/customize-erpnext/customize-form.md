## 15.4 Formular anpassen

Bevor wir uns an das Anpassungswerkzeug heran wagen, klicken Sie [hier](https://kb.frappe.io/kb/customization/form-architecture) um den Aufbau von Formularen in ERPNext zu verstehen. Das soll Ihnen dabei helfen das Anpassungswerkzeug effektiver zu nutzen.

Das Werkzeug "Formular anpassen" versetzt Sie in die Lage die Einstellungen eines Standardfeldes an Ihre Bedürfnisse anzupassen. Nehmen wir an, dass wir das Feld "Projektname" als zwingend erforderlich im Kundenaufrag kennzeichnen wollen. Im Folgenden finden Sie die Schritte, die dazu notwendig sind.

### Schritt 1: Zum benutzerdefinierten Formular gehen

Sie können zum benutzerdefinierten Formular folgendermaßen gelangen:

> Einstellungen > Anpassen > Benutzerdefiniertes Formular.

Der Systemmanager findet die Option "Benutzerdefiniertes Formular" auch in der Liste Kundenauftrag (bzw. jedes andere Formular für diesen Sachverhalt). 

![Formular anpassen - Listenansicht]({{docs_base_url}}/assets/old_images/erpnext/customize-form-list-view.png)

### Schritt 2: Wählen Sie den DocType/das Dokument

Wählen Sie jetzt den DocType/das Dokument aus, welcher/s das anzupassende Feld enthält.

![Formular anpassen - Dokument]({{docs_base_url}}/assets/old_images/erpnext/customize-form-document.png)

### Schritt 3: Bearbeiten Sie die Eigenschaften

Wenn Sie den DocType/das Dokument ausgewählt haben, werden alle Felder als Zeilen in der Tabelle des benutzerdefinierten Formulars aktualisiert. Scrollen sie bis zu dem Feld, das Sie bearbeiten wollen, in diesem Fall "Projektname".

Wenn Sie auf die Zeile "Projektname" klicken, werden Felder mit verschiedenen Eigenschaften für dieses Feld angezeigt. Um die Eigenschaft "Ist zwingend erforderlich" für ein Feld anzupassen gibt es ein Feld "Zwingend erfoderlich". Wenn Sie dieses Feld markieren, wird das Feld "Projektname" im Angebotsformular als zwingend erforderlich eingestellt.

![Formular anpassen - Zwingend erfoderliche Angaben]({{docs_base_url}}/assets/old_images/erpnext/customize-form-mandatory.png)

Genauso können Sie folgende Eigenschaften eines Feldes anpassen.

* Ändern von Feldtypen (Beispiel: Wenn Sie die Anzahl der Dezimalstellen erhöhen wollen, können Sie einige Felder von Float auf Währung umstellen).
* Ändern von Bezeichnungen, um sie an Ihre Branchen und Ihre Sprache anzupassen.
* Bestimmte Felder als zwingend erfoderlich einstellen.
* Bestimmte Felder verbergen.
* Ändern des Erscheinungsbildes (Anordnung von Feldern). Um das zu tun, wählen Sie ein Feld im Gitter aus und klicken Sie auf "Up" oder "Down" in der Werkzeugleiste des Gitters.
* Hinzufügen / Ändern von "Auswahl"-Optionen (Beispiel: Sie können bei Leads weitere Quellen hinzufügen).

### Schritt 4: Aktualisieren

![Formular anpassen - Aktualisieren]({{docs_base_url}}/assets/old_images/erpnext/customize-form-update.png)

Bevor Sie das Formular "Kundenauftrag" testen, sollten Sie den Cache leeren und den Inhalt des Browserfensters aktualiseren, um die Änderungen wirksam werden zu lassen.

Bei einem benutzerdefinierten Formular können Sie auch Anhänge erlauben, die maximal zulässige Anzahl von Anhängen festlegen und das Stanard-Druckformat einstellen.

> Anmerkung: Obwohl wir Ihnen möglichst viele Möglichkeiten einräumen wollen, Ihr ERP-System an die Erfordernisse Ihres Geschäftes anzupassen, empfehlen wir Ihnen, keine "wilden" Änderungen an den Formularen vorzunehmen. Die Änderungen können sich nämlich auf bestimmte Operationen auswirken und Ihre Formulare beschädigen. Machen Sie kleine Änderungen und prüfen Sie die Auswirkungen bevor Sie fortfahren.

Im Folgenden erhalten Sie eine Auflistung der Eigenschaften, die Sie für ein bestimmtes Feld eines benutzerdefinierten Formulars anpassen können.

Feldeigenschaft            Verwendungszweck

Beim Drucken verbergen     Verbirgt das Feld im Standard-Druckformat.
Verborgen                  Verbirgt das Feld im Datenerfassungs-Formular.
Ist zwingend erforderlich  Stellt das Feld als zwingend erforderlich ein.
Feldtyp                    Klicken Sie hier, um mehr über Feldtypen zu erfahren.
Optionen                   Hier können Sie Auswahlmöglichkeiten eines DropDown-Feldes auflisten. Für ein Verknüpfungsfeld kann auch der zutreffende DocType mit angegeben werden.
Beim Übertragen erlauben   Wenn Sie diesen Punkt aktivieren, kann der Benutzer den Wert des Feldes auch in einem übertragenen Formular aktualisieren.
Standard                   Der hier angegebene Wert wird beim Erstellen eines neuen Datensatzes angezogen.
Beschreibung               Enthält Erläuterungen zum Feld zum besseren Verständis.
Bezeichnung                Das ist der Feldname, wie er im Formular angezeigt wird.


<style>
    td {
    padding:5px 10px 5px 5px;
    };
    img {
    align:center;
    };
table, th, td {
    border: 1px solid black;
    border-collapse: collapse;
}
</style>
<table border="1" width="700px">
  <tbody>
    <tr>
      <td style="text-align: center;"><b>Field property</b></td>
      <td style="text-align: center;"><b>Purpose</b></td>
    </tr>
    <tr>
      <td>Print hide</td>
      <td>Checking it will hide field from Standard print format.</td>
    </tr>
    <tr>
      <td>Hidden</td>
      <td>Checking it field will hide field in the data entry form.</td>
    </tr>
    <tr>
      <td>Mandatory</td>
      <td>Checking it will set field as mandatory.</td>
    </tr>
    <tr>
      <td>Field Type</td>
      <td>Click <a href="https://erpnext.com/kb/customize/field-types">here</a> to learn about of fields types.</td>
    </tr>
    <tr>
      <td>Options</td>
      <td>Possible result for a drop down fields can be listed here. Also for a link field, relevant Doctype can be provided.</td>
    </tr>
    <tr>
      <td>Allow on submit</td>
      <td>Checking it will let user update value in field even in submitted form.</td>
    </tr>
    <tr>
      <td>Default</td>
      <td>Value defined in default will be pulled on new record creation.</td>
    </tr>
    <tr>
      <td>Description</td>
      <td>Gives field description for users understanding.</td>
    </tr>
    <tr>
      <td>Label</td>
      <td>Label is the field name which appears in form.</td>
    </tr>
  </tbody>
</table>

{next}
