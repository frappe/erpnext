# Benutzer-Berechtigungen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Verwenden Sie den Benutzerberechtigungen-Manager um den Zugriff eines Benutzers auf eine Menge von Dokumenten einzuschränken.

Rollenbasierte Berechtigungen definieren den Rahmen an Dokumententypen, innerhalb derer sich ein Benutzer mit einer Anzahl von Rollen bewegen darf. Sie können jedoch noch feinere Einstellungen treffen, wenn Sie für einen Benutzer Benutzerberechtigungen definieren. Wenn Sie bestimmte Dokumente in der Liste der Benutzerberechtigungen eintragen, dann können Sie den Zugriff dieses Benutzers auf bestimmte Dokumente eines bestimmten DocTypes begrenzen, unter der Bedingung, dass die Option "Benutzerberechtigungen anwenden" im Rollenberechtigungs-Manager aktiviert ist.

Beginnen Sie wie folgt:

> Einstellungen > Berechtigungen > Benutzerrechte-Manager


Abbildung: Übersicht aus dem Benutzerberechtigungs-Manager die aufzeigt, wie Benutzer nur auf bestimmte Firmen zugreifen können

#### Beispiel

Der Benutzer "aromn@example.com" hat die Rolle "Nutzer Vertrieb" und wir möchten die Zugriffsrechte des Benutzers so einschränken, dass er nur auf Datensätze einer bestimmten Firma, nämlich der Wind Power LLC, zugreifen kann.

1\. Wir fügen eine Benutzerberechtigungs-Zeile für die Firma hinzu.

Abbildung: Hinzufügen einer Zeile "Benutzer-Berechtigung" für die Kombination aus dem Benutzer "aromn@example.com" und der Firma Wind Power LLC

2\. Die Rolle "Alle" hat nur Leseberechtigungen für die Firma, "Benutzer-Berechtigungen anwenden" ist aktiviert.

Abbildung: Leseberechtigung mit aktivierter Option "Benutzer-Berechtigungen anwenden" für den DocType Firma

3\. Die oben abgebildete Kombination der zwei Regeln führt dazu, dass der Benutzer "aromn@example.com" für die Firma Wind Power LLC nur Leserechte hat.

Abbildung: Der Zugriff wird auf die Firma Wind Power LLC beschränkt

4\. Wir möchten nun diese Benutzer-Berechtigung für "Firma" auf andere Dokumente wie "Angebot", "Kundenauftrag" etc. übertragen. Diese Formulare haben **Verknüpfungsfelder zu "Firma"**. Als Ergebnis werden Benutzer-Berechtigungen von "Firma" auch auf diese Dokumente übertragen, was dazu führt, dass der Benutzer "aromn@example.com" auf diese Dokumente zugreifen kann, wenn Sie mit Wind Power LLC verbunden sind.

Abbildung: Benutzer mit der Rolle "Nutzer Vertrieb" können, basierend auf Ihren Benutzer-Berechtigungen, Angebote lesen, schreiben, erstellen, übertragen und stornieren, wenn "Benutzer-Berechtigungen anwenden" aktiviert ist.

Abbildung: Die Auflistung der Angebote enthält nur Ergebnisse für die Firma Wind Power LLC für den Benutzer "aromn@example.com"

5\. Benutzer-Berechtigungen werden automatisch auf Basis von verknüpften Feldern angewandt, genauso wie wir es bei den Angeboten gesehen haben. Aber: Das Lead-Formular hat vier Verknüpfungsfelder: "Region", "Firma", "Eigentümer des Leads" und "Nächster Kontakt durch". Nehmen wir an, Sie möchten dass die Leads den Zugriff des Benutzers basierend auf Ihrer Region einschränken, obwohl Sie für die DocTypes "Benutzer", "Region" und "Firma" Benutzer-Berechtigungen angelegt haben. Dann gehen Sie wir folgt vor: Aktivieren Sie die Option "Benutzer-Berechtigungen ignorieren" für die Verknüpfungsfelder "Firma", "Eigentümer des Leads" und "Nächster Kontakt durch".

Abbildung: Der Vertriebsmitarbeiter kann Leads lesen, schreiben und erstellen, eingeschränkt durch Benutzer-Berechtigungen.

Abbildung: Markieren Sie "Benutzer-Berechtigungen ignorieren" für die Felder "Firma", "Lead-Inhaber" und "Nächster Kontakt durch" über Setup > Anpassen > Formular anpassen > Lead.

Abbildung: Aufgrund der obigen Kombination kann der Benutzer "aromn@example.com" nur auf Leads der Region "United States" zugreifen.

{next}
