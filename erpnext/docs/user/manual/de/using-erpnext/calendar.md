# Kalender
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Der Kalender ist ein Werkzeug, mit dem Sie Ereignisse erstellen und teilen können und auch automatisch aus dem System erstellte Ereignisse sehen können.

Sie können die Kalenderansicht umschalten zwischen Monatsansicht, Wochenansicht und Tagesansicht.

### Ereignisse im Kalender erstellen

#### Ein Ereignis manuell erstellen

Um ein Ereignis manuell zu erstellen, sollten Sie zuerst die Kalenderansicht festlegen. Wenn sich der Start- und Endzeitpunkt am selben Tag befinden, gehen Sie zuerst in die Tagesansicht.

Diese Ansicht zeigt die 24 Stunden des Tages aufgeteilt in verschiedene Zeitfenster an. Klicken Sie für den Startzeitpunkt auf ein Zeitfenster und ziehen Sie den Rahmen auf bis Sie den Endzeitpunkt erreichen.

![Manuelle Kalenderereignisse]({{docs_base_url}}/assets/old_images/erpnext/calender-event-manually.png)

Auf Grundlage der Auswahl des Zeitfensters werden Start- und Endzeitpunkt in die Ereignisvorlage übernommen. Sie können dann noch die Bezeichnung des Ereignisses angeben und speichern.

#### Ereignis auf Grundlage eines Leads

Im Leadformular finden Sie die Felder "Nächster Kontakt durch" und "Nächstes Kontaktdatum". Wenn Sie in diesen Feldern einen Termin und eine Kontaktperson eintragen, wird automatisch ein Ereignis erstellt.

![Ereignis auf Grundlage eines Leads]({{docs_base_url}}/assets/old_images/erpnext/calender-event-lead.png)

#### Geburtstag

Auf Basis der in den Mitarbeiterstammdaten eingetragenen Geburtstage werden Geburtstagsereignisse erstellt.

### Wiederkehrende Ereignisse

Sie können Ereignisse als wiederkehrend in bestimmten Intervallen markieren, indem Sie "Dieses Ereignis wiederholen" aktivieren.

![Wiederkehrendes Kalenderereignis]({{docs_base_url}}/assets/old_images/erpnext/calender-event-recurring.png)

### Berechtigungen für ein Ereignis

Sie können ein Ereignis als privat oder öffentlich erstellen. Private Ereignisse können nur Sie und Benutzer, die in der Tabelle "Teilnehmer" ausgewählt wurden, sehen. Sie können Berechtigungen für Ereignisse nicht nur über den Benutzer, sondern auch über die Rolle setzen.

Ein öffentliches Ereignis wie ein Geburtstag ist für alle sichtbar.

![Berechtigungen für Kalenderereignisse]({{docs_base_url}}/assets/old_images/erpnext/calender-event-permission.png)

### Erinnerungen an Ereignisse

Es gibt zwei Arten, wie Sie eine Erinnerung zu einem Ereignis per E-Mail erhalten können.

#### Erinnerung im Ereignis aktivieren

Wenn Sie in der Ereignisvorlage den Punkt "E-Mail-Erinnerung am Morgen senden" anklicken, erhalten alle Teilnehmer an diesem Ereignis eine Benachrichtungs-E-Mail.

![Benachrichtigung über Kalenderereignisse]({{docs_base_url}}/assets/old_images/erpnext/calender-event-notification.png)

#### Einen täglichen E-Mail-Bericht erstellen

Wenn Sie für Kalenderereignisse Erinnerungen erhalten wollen, sollten Sie den täglichen E-Mail-Bericht für Kalenderereignisse einstellen.

Der tägliche E-Mail-Bericht kann eingestellt werden über:

> Einstellungen > E-Mail > Täglicher E-Mail-Bericht

![Täglicher E-Mail-Bericht]({{docs_base_url}}/assets/old_images/erpnext/calender-email-digest.png)

{next}
