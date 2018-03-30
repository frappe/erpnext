# Formular anpassen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Bevor wir uns an das Anpassungswerkzeug heran wagen, klicken Sie [hier](https://kb.frappe.io/kb/customization/form-architecture) um den Aufbau von Formularen in ERPNext zu verstehen. Das soll Ihnen dabei helfen das Anpassungswerkzeug effektiver zu nutzen.

Das Werkzeug "Formular anpassen" versetzt Sie in die Lage die Einstellungen eines Standardfeldes an Ihre Bedürfnisse anzupassen. Nehmen wir an, dass wir das Feld "Projektname" als zwingend erforderlich im Kundenaufrag kennzeichnen wollen. Im Folgenden finden Sie die Schritte, die dazu notwendig sind.

### Schritt 1: Zum benutzerdefinierten Formular gehen

Sie können zum benutzerdefinierten Formular folgendermaßen gelangen:

> Einstellungen > Anpassen > Benutzerdefiniertes Formular.

Der Systemmanager findet die Option "Benutzerdefiniertes Formular" auch in der Liste Kundenauftrag (bzw. jedes andere Formular für diesen Sachverhalt). 

![Formular anpassen - Listenansicht](/docs/assets/old_images/erpnext/customize-form-list-view.png)

### Schritt 2: Wählen Sie den DocType/das Dokument

Wählen Sie jetzt den DocType/das Dokument aus, welcher/s das anzupassende Feld enthält.

![Formular anpassen - Dokument](/docs/assets/old_images/erpnext/customize-form-document.png)

### Schritt 3: Bearbeiten Sie die Eigenschaften

Wenn Sie den DocType/das Dokument ausgewählt haben, werden alle Felder als Zeilen in der Tabelle des benutzerdefinierten Formulars aktualisiert. Scrollen sie bis zu dem Feld, das Sie bearbeiten wollen, in diesem Fall "Projektname".

Wenn Sie auf die Zeile "Projektname" klicken, werden Felder mit verschiedenen Eigenschaften für dieses Feld angezeigt. Um die Eigenschaft "Ist zwingend erforderlich" für ein Feld anzupassen gibt es ein Feld "Zwingend erfoderlich". Wenn Sie dieses Feld markieren, wird das Feld "Projektname" im Angebotsformular als zwingend erforderlich eingestellt.

![Formular anpassen - Zwingend erfoderliche Angaben](/docs/assets/old_images/erpnext/customize-form-mandatory.png)

Genauso können Sie folgende Eigenschaften eines Feldes anpassen.

* Ändern von Feldtypen (Beispiel: Wenn Sie die Anzahl der Dezimalstellen erhöhen wollen, können Sie einige Felder von Float auf Währung umstellen).
* Ändern von Bezeichnungen, um sie an Ihre Branchen und Ihre Sprache anzupassen.
* Bestimmte Felder als zwingend erfoderlich einstellen.
* Bestimmte Felder verbergen.
* Ändern des Erscheinungsbildes (Anordnung von Feldern). Um das zu tun, wählen Sie ein Feld im Gitter aus und klicken Sie auf "Up" oder "Down" in der Werkzeugleiste des Gitters.
* Hinzufügen / Ändern von "Auswahl"-Optionen (Beispiel: Sie können bei Leads weitere Quellen hinzufügen).

### Schritt 4: Aktualisieren

![Formular anpassen - Aktualisieren](/docs/assets/old_images/erpnext/customize-form-update.png)

Bevor Sie das Formular "Kundenauftrag" testen, sollten Sie den Cache leeren und den Inhalt des Browserfensters aktualiseren, um die Änderungen wirksam werden zu lassen.

Bei einem benutzerdefinierten Formular können Sie auch Anhänge erlauben, die maximal zulässige Anzahl von Anhängen festlegen und das Stanard-Druckformat einstellen.

> Anmerkung: Obwohl wir Ihnen möglichst viele Möglichkeiten einräumen wollen, Ihr ERP-System an die Erfordernisse Ihres Geschäftes anzupassen, empfehlen wir Ihnen, keine "wilden" Änderungen an den Formularen vorzunehmen. Die Änderungen können sich nämlich auf bestimmte Operationen auswirken und Ihre Formulare beschädigen. Machen Sie kleine Änderungen und prüfen Sie die Auswirkungen bevor Sie fortfahren.

Im Folgenden erhalten Sie eine Auflistung der Eigenschaften, die Sie für ein bestimmtes Feld eines benutzerdefinierten Formulars anpassen können.


<table border="1" width="700px">
  <tbody>
    <tr>
      <td style="text-align: center;"><b>Feldeigenschaft</b></td>
      <td style="text-align: center;"><b>Verwendungszweck</b></td>
    </tr>
    <tr>
      <td>Beim Drucken verbergen</td>
      <td>Verbirgt das Feld beim Standarddruck</td>
    </tr>
    <tr>
      <td>Verborgen</td>
      <td>Verbirgt das Feld im Formular zur Datenerfassung.</td>
    </tr>
    <tr>
      <td>Zwingend erforderlich</td>
      <td>Stellt das Feld als zwingend erforderlich ein.</td>
    </tr>
    <tr>
      <td>Feldtyp</td>
      <td>Klicken Sie <a href="/docs/user/manual/en/customize-erpnext/articles/field-types">hier</a> um mehr über Feldtypen zu erfahren.</td>
    </tr>
    <tr>
      <td>Optionen</td>
      <td>Hier können Sie Auswahlmöglichkeiten eines DropDown-Feldes auflisten. Für ein Verknüpfungsfeld kann auch der zutreffende DocType mit angegeben werden.</td>
    </tr>
    <tr>
      <td>Beim Übertragen erlauben</td>
      <td>Wenn Sie diesen Punkt aktivieren, kann der Benutzer den Wert des Feldes auch in einem übertragenen Formular aktualisieren.</td>
    </tr>
    <tr>
      <td>Standard</td>
      <td>Der hier angegebene Wert wird beim Erstellen eines neuen Datensatzes angezogen.</td>
    </tr>
    <tr>
      <td>Beschreibung</td>
      <td>Enthält Erläuterungen zum Feld zum besseren Verständis.</td>
    </tr>
    <tr>
      <td>Bezeichnung</td>
      <td>Das ist der Feldname, wie er im Formular angezeigt wird.</td>
    </tr>
  </tbody>
</table>

{next}
