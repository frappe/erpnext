# Werkzeug zum Datenimport
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Das Werkzeug zum Datenimport ist ein großartiger Weg um große Mengen an Daten, speziell Stammdaten, in das System hochzuladen oder zu bearbeiten.

Um das Werkzeug zum Datenimport zu öffnen, gehen Sie entweder zu den Einstellungen oder zur Transaktion, für die Sie importieren wollen. Wenn der Datenimport erlaubt ist, sehen Sie eine Importschaltfläche:

<img alt="Importvorgang starten" class="screenshot" src="/docs/assets/img/setup/data-import/data-import-1.png">

Das Werkzeug hat zwei Abschnitte, einen um eine Vorlage herunter zu laden, und einen zweiten um Daten hoch zu laden.

(Anmerkung: Für den Import sind nur die DocTypes zugelassen, deren Dokumenttyp "Stammdaten" ist, oder bei denen die Einstellung "Import erlauben" aktiviert ist.)

### 1. Herunterladen der Vorlage

Daten werden in ERPNext in Tabellen gespeichert, sehr ähnlich einer Tabellenkalkulation mit Spalten und Zeilen voller Daten. Jede Instanz in ERPNext kann mehrere verschiedene mit Ihr verbundene Untertabellen haben. Die Untertabellen sind mit Ihren übergeordneten Tabellen verknüpft und werden dort eingesetzt, wo es für eine Eigenschaft mehrere verschiedene Werte gibt. So kann z. B. ein Artikel mehrere verschiedene Preise haben, eine Rechnung hat mehrere verschiedene Artikel usw.

<img alt="Vorlage herunterladen" class="screenshot" src="/docs/assets/img/setup/data-import/data-import-2.png">

* Klicken Sie auf die Tabelle, die Sie herunter laden wollen, oder auf "Alle Tabellen".
* Für Massenbearbeitung klicken Sie auf "Mit Daten herunterladen".

### 2. Füllen Sie die Vorlage aus

Öffnen Sie die Vorlage nach dem Herunterladen in einer Tabellenkalkulationsanwendung und fügen Sie die Daten unterhalb der Spaltenköpfe ein.

![Tabellenblatt](/docs/assets/old_images/erpnext/import-3.png)

Exportieren Sie dann Ihre Vorlage oder speichern Sie sie im CSV-Format (**Comma Separated Values**).

![Tabellenblatt](/docs/assets/old_images/erpnext/import-4.png)

### 3. Hochladen der CSV-Datei

Fügen Sie abschliessend die CSV-Datei im Abschnitt Import hinzu. Klicken Sie auf die Schaltfläche "Hochladen und Importieren".

<img alt="Upload" class="screenshot" src="/docs/assets/img/setup/data-import/data-import-3.png">

#### Anmerkungen

1. Stellen Sie sicher, dass Sie als Verschlüsselung UTF-8 verwenden, wenn Ihre Anwendung das zulässt.
2. Lassen Sie die Spalte ID für einen neuen Datensatz leer.

### 4. Hochladen aller Tabellen (übergeordnete und Untertabellen)

Wenn Sie alle Tabellen auswählen, dann erhalten Sie Spalten für alle Tabellen in einer Zeile gertrennt durch ~ Spalten.

Wenn Sie mehrere verschiedene Unterzeilen haben, dann müssen Sie einen neuen Hauptartikel in einer neuen Zeile eintragen. Sehen Sie hierzu das Beispiel unten:


    Main Table                          ~   Child Table
    Spalte 1    Spalte 2    Spalte 3    ~   Spalte 1    Spalte 2    Spalte 3
    v11         v12         v13             c11         c12         c13
                                            c14         c15         c17
    v21         v22         v23             c21         c22         c23


Um zu sehen, wie das gemacht wird, geben Sie manuell über Formulare einige Datensätze ein und exportieren Sie "Alle Tabellen" über "Mit Daten herunterladen".

### 5. Überschreiben

ERPNext ermöglicht es Ihnen auch alle oder bestimmte Spalten zu überschreiben. Wenn Sie bestimmte Spalten aktualisieren möchten, können Sie die Vorlage mit Daten herunter laden. Vergessen Sie nicht die Box "Überschreiben" zu markieren, bevor sie hochladen.

Anmerkung: Wenn Sie "Überschreiben" auswählen, werden alle Unterdatensätze eines übergeordneten Elements gelöscht.

### 6. Einschränkungen beim Hochladen

ERPNext begrenzt die Menge an Daten, die Sie in einer Datei hochladen können. Die Menge kann sich je nach Datentyp unterscheiden. Normalerweise kann man problemlos ungefähr 1.000 Zeilen einer Tabelle in einem Vorgang hochladen. Wenn das System den Vorgang nicht akzeptiert, sehen Sie eine Fehlermeldung.

Warum das alles? Wenn Sie zuviele Daten hochladen, kann das System abstürzen, im Besonderen dann, wenn andere Benutzer parallel arbeiten. Daher begrenzt ERPNext die Anzahl von Schreibvorgängen, die Sie mit einer Eingabe verarbeiten können.

---

#### Wie fügen Sie Dateien an?

Wenn Sie ein Formular öffnen, dann sehen Sie in der Seitenleiste rechts einen Abschnitt zum Anfügen von Dateien. Klicken Sie auf "Hinzufügen" und wählen Sie die Datei aus, die Sie anfügen möchten. Klicken Sie auf "Hochladen" und die Sache ist erledigt.

### Was ist eine CSV-Datei?
Eine CSV (Durch Kommas getrennte Werte)-Datei ist ein Datensatz, den Sie in ERPNext hochladen können um verschiedene Daten zu aktualisieren. Jedes gebräuchliche Tabellenkalkulationsprogramm wie MS-Excel oder OpenOffice Spreadsheet kann im CSV-Format abspeichern.
Wenn Sie Microsoft Excel benutzen und nicht-englische Zeichen verwenden, dann sollten Sie Ihre Datei UTF-8-kodiert abspeichern. Bei älteren Versionen von Excel gibt es keinen eindeutigen Weg als UTF-8 zu speichern. Deshalb können Sie die Datei auch ganz einfach als CSV abspeichern, dann mit Notepad öffnen und als UTF-8 abspeichern. (Microsoft Excel kann das leider nicht.)

{next}
