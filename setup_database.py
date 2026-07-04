"""Creates a self-contained Chinook-style SQLite database (chinook.db).

Run this once before starting the app:  python setup_database.py
Re-run it any time to reset the data (e.g. after testing a DELETE query).
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "chinook.db")

SCHEMA = """
DROP TABLE IF EXISTS invoice_items;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS tracks;
DROP TABLE IF EXISTS albums;
DROP TABLE IF EXISTS artists;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
    EmployeeId INTEGER PRIMARY KEY,
    FirstName  TEXT,
    LastName   TEXT,
    Title      TEXT,
    Email      TEXT
);
CREATE TABLE customers (
    CustomerId INTEGER PRIMARY KEY,
    FirstName  TEXT,
    LastName   TEXT,
    Country    TEXT,
    Email      TEXT
);
CREATE TABLE genres (
    GenreId INTEGER PRIMARY KEY,
    Name    TEXT
);
CREATE TABLE artists (
    ArtistId INTEGER PRIMARY KEY,
    Name     TEXT
);
CREATE TABLE albums (
    AlbumId  INTEGER PRIMARY KEY,
    Title    TEXT,
    ArtistId INTEGER REFERENCES artists(ArtistId)
);
CREATE TABLE tracks (
    TrackId      INTEGER PRIMARY KEY,
    Name         TEXT,
    AlbumId      INTEGER REFERENCES albums(AlbumId),
    GenreId      INTEGER REFERENCES genres(GenreId),
    Composer     TEXT,
    Milliseconds INTEGER,
    UnitPrice    REAL
);
CREATE TABLE invoices (
    InvoiceId      INTEGER PRIMARY KEY,
    CustomerId     INTEGER REFERENCES customers(CustomerId),
    InvoiceDate    TEXT,
    BillingCountry TEXT,
    Total          REAL
);
CREATE TABLE invoice_items (
    InvoiceLineId INTEGER PRIMARY KEY,
    InvoiceId     INTEGER REFERENCES invoices(InvoiceId),
    TrackId       INTEGER REFERENCES tracks(TrackId),
    UnitPrice     REAL,
    Quantity      INTEGER
);
"""

EMPLOYEES = [
    (1, "Andrew", "Adams",    "General Manager",     "andrew@chinookcorp.com"),
    (2, "Nancy",  "Edwards",  "Sales Manager",       "nancy@chinookcorp.com"),
    (3, "Jane",   "Peacock",  "Sales Support Agent", "jane@chinookcorp.com"),
    (4, "Margaret","Park",    "Sales Support Agent", "margaret@chinookcorp.com"),
    (5, "Steve",  "Johnson",  "Sales Support Agent", "steve@chinookcorp.com"),
    (6, "Michael","Mitchell", "IT Manager",          "michael@chinookcorp.com"),
    (7, "Robert", "King",     "IT Staff",            "robert@chinookcorp.com"),
    (8, "Laura",  "Callahan", "IT Staff",            "laura@chinookcorp.com"),
]

CUSTOMERS = [
    (1,  "Luis",     "Goncalves", "Brazil",        "luisg@embraer.com.br"),
    (2,  "Leonie",   "Kohler",    "Germany",       "leonekohler@surfeu.de"),
    (3,  "Francois", "Tremblay",  "Canada",        "ftremblay@gmail.com"),
    (4,  "Bjorn",    "Hansen",    "Norway",        "bjorn.hansen@yahoo.no"),
    (5,  "Frantisek","Wichterlova","Czech Republic","frantisekw@jetbrains.com"),
    (6,  "Helena",   "Holy",      "Czech Republic","hholy@gmail.com"),
    (7,  "Astrid",   "Gruber",    "Austria",       "astrid.gruber@apple.at"),
    (8,  "Daan",     "Peeters",   "Belgium",       "daan_peeters@apple.be"),
    (9,  "Kara",     "Nielsen",   "Denmark",       "kara.nielsen@jubii.dk"),
    (10, "Eduardo",  "Martins",   "Brazil",        "eduardo@woodstock.com.br"),
    (11, "Alexandre","Rocha",     "Brazil",        "alero@uol.com.br"),
    (12, "Roberto",  "Almeida",   "Brazil",        "roberto.almeida@riotur.gov.br"),
    (13, "Jennifer", "Peterson",  "Canada",        "jenniferp@rogers.ca"),
    (14, "Mark",     "Philips",   "Canada",        "mphilips12@shaw.ca"),
    (15, "Frank",    "Harris",    "USA",           "fharris@google.com"),
    (16, "Jack",     "Smith",     "USA",           "jacksmith@microsoft.com"),
    (17, "Michelle", "Brooks",    "USA",           "michelleb@aol.com"),
    (18, "Tim",      "Goyer",     "USA",           "tgoyer@apple.com"),
]

GENRES = [
    (1, "Rock"), (2, "Jazz"), (3, "Metal"), (4, "Alternative & Punk"),
    (5, "Blues"), (6, "Latin"), (7, "Pop"), (8, "Classical"),
]

ARTISTS = [
    (1, "AC/DC"), (2, "Accept"), (3, "Aerosmith"), (4, "Alanis Morissette"),
    (5, "Metallica"), (6, "Queen"), (7, "Miles Davis"), (8, "U2"),
    (9, "Led Zeppelin"), (10, "The Rolling Stones"),
]

ALBUMS = [
    (1, "For Those About To Rock", 1),
    (2, "Balls to the Wall", 2),
    (3, "Toys in the Attic", 3),
    (4, "Jagged Little Pill", 4),
    (5, "Master of Puppets", 5),
    (6, "A Night at the Opera", 6),
    (7, "Kind of Blue", 7),
    (8, "The Joshua Tree", 8),
    (9, "IV", 9),
    (10, "Let It Bleed", 10),
]

# (TrackId, Name, AlbumId, GenreId, Composer, Milliseconds, UnitPrice)
TRACKS = [
    (1,  "For Those About To Rock (We Salute You)", 1, 1, "Angus Young", 343719, 0.99),
    (2,  "Balls to the Wall", 2, 3, "U. Dirkschneider", 342562, 0.99),
    (3,  "Walk This Way", 3, 1, "Steven Tyler", 331180, 0.99),
    (4,  "Sweet Emotion", 3, 1, "Steven Tyler", 271266, 0.99),
    (5,  "You Oughta Know", 4, 4, "Alanis Morissette", 249234, 0.99),
    (6,  "Ironic", 4, 7, "Alanis Morissette", 229825, 0.99),
    (7,  "Master of Puppets", 5, 3, "Metallica", 515401, 1.29),
    (8,  "Battery", 5, 3, "Metallica", 312851, 1.29),
    (9,  "Bohemian Rhapsody", 6, 1, "Freddie Mercury", 355168, 1.29),
    (10, "Love of My Life", 6, 1, "Freddie Mercury", 219266, 0.99),
    (11, "So What", 7, 2, "Miles Davis", 562000, 1.29),
    (12, "Blue in Green", 7, 2, "Miles Davis", 337000, 0.99),
    (13, "With or Without You", 8, 1, "U2", 299413, 0.99),
    (14, "Where the Streets Have No Name", 8, 1, "U2", 336933, 0.99),
    (15, "Stairway to Heaven", 9, 1, "Jimmy Page", 482830, 1.29),
    (16, "Black Dog", 9, 1, "Jimmy Page", 296520, 0.99),
    (17, "Gimme Shelter", 10, 1, "Keith Richards", 271266, 0.99),
    (18, "You Can't Always Get What You Want", 10, 1, "Mick Jagger", 448633, 0.99),
    (19, "Thunderstruck", 1, 1, "Angus Young", 292000, 0.99),
    (20, "Enter Sandman", 5, 3, "Metallica", 331000, 1.29),
]

# (InvoiceId, CustomerId, InvoiceDate, BillingCountry, Total)
INVOICES = [
    (1,  2,  "2024-01-01", "Germany",        1.98),
    (2,  4,  "2024-01-02", "Norway",         3.96),
    (3,  8,  "2024-01-03", "Belgium",        5.94),
    (4,  14, "2024-01-06", "Canada",         8.91),
    (5,  15, "2024-01-11", "USA",           13.86),
    (6,  1,  "2024-02-01", "Brazil",         6.93),
    (7,  10, "2024-02-05", "Brazil",         4.95),
    (8,  16, "2024-02-09", "USA",           11.88),
    (9,  17, "2024-02-14", "USA",            2.97),
    (10, 3,  "2024-03-01", "Canada",         9.90),
    (11, 5,  "2024-03-04", "Czech Republic", 7.92),
    (12, 6,  "2024-03-10", "Czech Republic", 3.96),
    (13, 7,  "2024-03-15", "Austria",        5.94),
    (14, 18, "2024-03-20", "USA",           15.84),
    (15, 1,  "2024-04-01", "Brazil",         1.98),
    (16, 11, "2024-04-05", "Brazil",         8.91),
    (17, 12, "2024-04-11", "Brazil",         6.93),
    (18, 13, "2024-04-18", "Canada",        12.87),
    (19, 9,  "2024-05-02", "Denmark",        4.95),
    (20, 15, "2024-05-10", "USA",            9.90),
    (21, 16, "2024-05-19", "USA",            7.92),
    (22, 2,  "2024-06-01", "Germany",       10.89),
    (23, 4,  "2024-06-08", "Norway",         2.97),
    (24, 17, "2024-06-15", "USA",           13.86),
    (25, 18, "2024-06-22", "USA",            5.94),
    (26, 1,  "2024-07-01", "Brazil",         3.96),
    (27, 10, "2024-07-09", "Brazil",        11.88),
    (28, 15, "2024-07-16", "USA",            8.91),
    (29, 3,  "2024-07-23", "Canada",         6.93),
    (30, 6,  "2024-07-30", "Czech Republic", 4.95),
]

# (InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity)
INVOICE_ITEMS = []
_line = 1
for inv in INVOICES:
    inv_id = inv[0]
    # attach 2 tracks per invoice in a simple rotating pattern
    t1 = ((inv_id - 1) % 20) + 1
    t2 = (inv_id % 20) + 1
    for t in (t1, t2):
        INVOICE_ITEMS.append((_line, inv_id, t, 0.99, 1))
        _line += 1


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    cur.executemany("INSERT INTO employees VALUES (?,?,?,?,?)", EMPLOYEES)
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", CUSTOMERS)
    cur.executemany("INSERT INTO genres VALUES (?,?)", GENRES)
    cur.executemany("INSERT INTO artists VALUES (?,?)", ARTISTS)
    cur.executemany("INSERT INTO albums VALUES (?,?,?)", ALBUMS)
    cur.executemany("INSERT INTO tracks VALUES (?,?,?,?,?,?,?)", TRACKS)
    cur.executemany("INSERT INTO invoices VALUES (?,?,?,?,?)", INVOICES)
    cur.executemany("INSERT INTO invoice_items VALUES (?,?,?,?,?)", INVOICE_ITEMS)
    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}")
    print(f"  employees={len(EMPLOYEES)}  customers={len(CUSTOMERS)}  "
          f"tracks={len(TRACKS)}  invoices={len(INVOICES)}")


if __name__ == "__main__":
    build_database()
