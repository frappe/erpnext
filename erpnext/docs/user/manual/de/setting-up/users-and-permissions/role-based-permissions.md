## 2.2.2 Rollenbasierte Berechtigungen

ERPNext arbeitet mit einem rollenbasierten Berechtigungssystem. Das heißt, dass Sie Benutzern Rollen zuordnen können und Rollen Berechtigungen erteilen können. Die Struktur der Berechtigungen erlaubt es Ihnen weiterhin verschiedene Berechtigungsregeln für unterschiedliche Felder zu definieren, wobei das **Konzept der Berechtigungsebenen** für Felder verwendet wird. Wenn einem Kunden einmal Rollen zugeordnet worden sind, haben Sie darüber die Möglichkeit, den Zugriff eines Benutzers auf bestimmte Dokumente zu beschränken.

Wenn Sie das tun wollen, gehen Sie zu:

Einstellungen > Berechtigungen > Rollenberechtigungen-Manager



Berechtigungen werden angewandt auf einer Kombination von:

* **Rollen:** Wie wir schon angesprochen haben, werden Benutzern Rollen zugeordnet, und auf diese wiederum werden Berechtigungsregeln angewandt.
_Beispiele für Rollen sind der "Kontenmanager", der "Mitarbeiter" und der "Nutzer Personalabteilung"._
* **Dokumenttypen:** Jeder Dokumententyp, jede Vorlage und jede Transaktion hat eine eigene Liste von rollenbasierten Berechtigungen.
_Beispiele für Dokumententypen sind: "Ausgangsrechnung", "Urlaubsantrag", "Lagerbuchung", usw._
* **Berechtigungs"ebenen":** Sie können in jedem Dokument Felder nach "Ebenen" gruppieren. Jede Gruppierung von Feldern wird mit einer eindeutigen Nummer (0, 1, 2, 3, usw.) versehen. Auf jede Feldgruppierung kann ein eigenständiger Satz von Berechtigungsregeln angewandt werden. Standardmäßig haben alle Felder die Ebene 0.
_Die Berechtigungsebene verbindet die Gruppierung der Felder der Ebene X mit einer Berechtigungsregel der Ebene X._
* **Dokumentenphasen:** Berechtigungen werden zu jeder Phase eines Dokumentes angewandt, wie z. B. Erstellung, Speicherung, Übetragung, Stornierung und Änderung. Eine Rolle kann die Berechtigung haben zu drucken, per E-Mail zu versenden, Daten zu importieren oder zu exportieren, auf Berichte zuzugreifen oder Benutzerberechtigungen zu definieren.
* **Benutzerberechtigungen anwenden:** Dieser Schalter entscheidet, ob für eine Rolle in einer bestimmten Dokumentenphase Benutzerberechtigungen gültig sind.

Wenn dieser Punkt aktiviert ist, kann ein Benutzer mit dieser Rolle nur auf bestimmte Dokumente dieses Dokumententyps zugreifen. Dieser spezielle Dokumentenzugriff wird über die Liste der Benutzerberechtigungen definiert. Zusätzlich werden Benutzerberechtigungen, die für andere Dokumententypen definiert wurden, ebenfalls angewandt, wenn Sie mit dem aktuellen Dokumententyp über Verknüpfungsfelder verbunden sind.

Um Benutzerberechtigungen zu setzen, gehen Sie zu:

Einstellungen > Berechtigungen > Benutzerrechte-Manager



---

**Um eine neue Regel hinzuzufügen**, klicken Sie auf die Schaltfläche "Benutzereinschränkung hinzufügen". Es öffnet sich ein Popup-Fenster und bittet Sie eine Rolle und eine Berechtigungsebene auszuwählen. Wenn Sie diese Auswahl treffen und auf "Hinzufügen" klicken, wird in der Tabelle der Regeln eine neue Zeile eingefügt.

---

Der Urlaubsantrag ist ein gutes **Beispiel**, welches alle Bereiche des Berechtigungssystems abdeckt.



1\. **Er sollte von einem "Mitarbeiter" erstellt werden.** Aus diesem Grund sollte die Rolle "Mitarbeiter" Berechtigungen zum Lesen, Schreiben und Erstellen haben.



2\. **Ein Mitarbeiter sollte nur auf seine/Ihre eigenen Urlaubsanträge zugreifen können.** Daher sollte der Punkt "Benutzerberechtigungen anwenden" für die Rolle "Mitarbeiter" aktiviert sein und es sollte ein Datensatz "Benutzerberechtigung" für jede Kombination von Benutzer und Mitarbeiter erstellt werden. (Dieser Aufwand reduziert sich für den Dokumententyp, indem über das Programm Datensätze für Benutzerberechtigungen erstellt werden.)



3\. **Der Personalmanager sollte alle Urlaubsanträge sehen können.** Erstellen Sie für den Personalmanager eine Berechtigungsregel auf der Ebene 0 mit Lese-Rechten. Die Option "Benutzerberechtigungen anwenden" sollte deaktiviert sein.



4\. **Der Urlaubsgenehmiger sollte die ihn betreffenden Urlaubsanträge lesen und aktualisieren können.** Der Urlaubsgenehmiger erhält Lese- und Schreibzugriff auf Ebene 0, und die Option "Benutzerberechtigungen anwenden" wird aktiviert. Zutreffende Mitarbeiter-Dokumente sollten in den Benutzerberechtigungen des Urlaubsgenehmigers aufgelistet sein. (Dieser Aufwand reduziert sich für Urlaubsgenehmiger, die in Mitarbeiterdokumenten aufgeführt werden, indem über das Programm Datensätze für Benutzerberechtigungen erstellt werden.)



5\. **Ein Urlaubsantrag sollte nur von einem Mitarbeiter der Personalverwaltung oder einem Urlaubsgenehmiger bestätigt oder abgelehnt werden können.** Das Statusfeld des Urlaubsantrags wird auf Ebene 1 gesetzt. Mitarbeiter der Personalverwaltung und Urlaubsgenehmiger bekommen Lese- und Schreibrechte für Ebene 1, während allen anderen Leserechte für Ebene 1 gegeben werden.



6\. **Der Mitarbeiter der Personalverwaltung sollte die Möglichkeit haben Urlaubsanträge an seine Untergebenen zu delegieren.** Er erhält die Erlaubis Benutzerberechtigungen einzustellen. Ein Nutzer mit der Rolle "Benutzer Personalverwaltung" wäre dann also in der Lage Benutzer-Berechtigungen und Urlaubsanträge für andere Benutzer zu definieren.



{next}
