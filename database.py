"""
database.py - everything that talks to SQLite lives here.

Why a separate file? Keeping SQL out of the web routes (app.py) means you can
test the database on its own:   python database.py   (creates + seeds the DB)

Tables
------
mandals : one row per mandal (name, area, pin position, ...)
reviews : many reviews per mandal (overall / crowd / parking ratings)
photos  : many photos per mandal (we store only the file NAME, not the image)
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mandals.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS mandals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL UNIQUE COLLATE NOCASE,
    area             TEXT NOT NULL,
    description      TEXT DEFAULT '',
    nearest_station  TEXT DEFAULT '',
    established_year INTEGER,
    lat              REAL NOT NULL,
    lng              REAL NOT NULL,
    coords_verified  INTEGER NOT NULL DEFAULT 0,  -- 0 = approximate pin, 1 = checked
    maps_query       TEXT,                        -- optional text for Google Maps search
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    mandal_id  INTEGER NOT NULL REFERENCES mandals(id) ON DELETE CASCADE,
    reviewer   TEXT DEFAULT 'Anonymous',
    overall    INTEGER NOT NULL CHECK (overall BETWEEN 1 AND 5),
    crowd      INTEGER NOT NULL CHECK (crowd   BETWEEN 1 AND 5),  -- 1 calm ... 5 packed
    parking    INTEGER NOT NULL CHECK (parking BETWEEN 1 AND 5),  -- 1 impossible ... 5 easy
    comment    TEXT DEFAULT '',
    is_sample  INTEGER NOT NULL DEFAULT 0,        -- 1 = placeholder rating from seed data
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS photos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    mandal_id  INTEGER NOT NULL REFERENCES mandals(id) ON DELETE CASCADE,
    filename   TEXT NOT NULL,
    uploader   TEXT DEFAULT 'Anonymous',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# ---------------------------------------------------------------------------
# SEED DATA
# Pins are APPROXIMATE (locality level, roughly +/- 300-500 m). To verify one:
# open Google Maps, right-click the exact spot, click the coordinates to copy
# them, paste here and set verified=1.
# `sample` = (overall, crowd, parking) placeholder ratings so the filters have
# something to show. They are NOT real survey data - replace them with real
# reviews from classmates/visitors.
# Years are included only where a published source was found.
# ---------------------------------------------------------------------------
SEED_MANDALS = [
    dict(name="Lalbaugcha Raja", area="Lalbaug", lat=18.9870, lng=72.8337,
         year=1934, station="Chinchpokli / Currey Road",
         description="Mumbai's most visited public Ganpati, also called Navsacha Ganpati. Expect very long darshan queues.",
         maps_query="Lalbaugcha Raja, Lalbaug, Mumbai", sample=(4, 5, 1)),
    dict(name="Mumbaicha Raja (Ganesh Galli)", area="Lalbaug", lat=18.9846, lng=72.8330,
         year=1928, station="Chinchpokli",
         description="A few lanes from Lalbaugcha Raja, known for elaborate themed sets.",
         maps_query="Ganesh Galli Mumbaicha Raja, Lalbaug, Mumbai", sample=(4, 4, 1)),
    dict(name="Chinchpoklicha Chintamani", area="Chinchpokli", lat=18.9810, lng=72.8310,
         year=None, station="Chinchpokli",
         description="One of the best-known mandals of the Chinchpokli-Lalbaug belt.",
         maps_query="Chinchpoklicha Chintamani, Chinchpokli, Mumbai", sample=(4, 4, 1)),
    dict(name="Kalachowkicha Mahaganapati", area="Kalachowki", lat=18.9840, lng=72.8380,
         year=None, station="Currey Road / Chinchpokli",
         description="Large neighbourhood mandal in the Kalachowki area.",
         maps_query="Kalachowkicha Mahaganapati, Kalachowki, Mumbai", sample=(4, 3, 2)),
    dict(name="Parelcha Raja", area="Parel", lat=18.9960, lng=72.8390,
         year=None, station="Parel / Elphinstone Road",
         description="Respected old-Parel neighbourhood mandal.",
         maps_query="Parelcha Raja, Parel, Mumbai", sample=(4, 3, 2)),
    dict(name="Dongricha Raja", area="Dongri", lat=18.9590, lng=72.8340,
         year=1939, station="Sandhurst Road",
         description="Often called the 'King of South Mumbai', a long-running Dongri mandal.",
         maps_query="Dongricha Raja, Dongri, Mumbai", sample=(4, 3, 2)),
    dict(name="Khetwadicha Ganraj", area="Khetwadi", lat=18.9578, lng=72.8182,
         year=1959, station="Grant Road / Charni Road",
         description="Khetwadi 12th Lane. Famed for tall idols and detailed themes; several other mandals share the lanes nearby.",
         maps_query="Khetwadicha Ganraj, Khetwadi 12th Lane, Mumbai", sample=(5, 4, 2)),
    dict(name="Girgaoncha Raja", area="Girgaon", lat=18.9534, lng=72.8189,
         year=1928, station="Charni Road",
         description="One of the oldest sarvajanik Ganpatis of South Mumbai, close to Girgaon Chowpatty.",
         maps_query="Girgaoncha Raja, Girgaon, Mumbai", sample=(5, 4, 2)),
    dict(name="Fortcha Raja", area="Fort", lat=18.9345, lng=72.8338,
         year=None, station="CSMT / Churchgate",
         description="Fort Vibhag Ganeshotsav Mandal; easy to combine with a walk around Fort.",
         maps_query="Fortcha Raja Fort Vibhag Ganeshotsav Mandal, Mumbai", sample=(4, 3, 3)),
    dict(name="Colabacha Samrat", area="Colaba", lat=18.9168, lng=72.8267,
         year=1993, station="Churchgate (then taxi) / Colaba bus depot",
         description="Neighbourhood mandal in Colaba, a calmer option than the Lalbaug belt.",
         maps_query="Colabacha Samrat, Colaba, Mumbai", sample=(4, 2, 3)),
]


def get_conn():
    """Open a connection. Rows behave like dicts (row['name'])."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite needs this switched on
    return conn


def init_db():
    """Create tables, and seed the starter mandals only if the table is empty."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM mandals").fetchone()[0]
        if count == 0:
            for m in SEED_MANDALS:
                cur = conn.execute(
                    """INSERT INTO mandals
                       (name, area, description, nearest_station, established_year,
                        lat, lng, coords_verified, maps_query)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                    (m["name"], m["area"], m["description"], m["station"],
                     m["year"], m["lat"], m["lng"], m["maps_query"]),
                )
                overall, crowd, parking = m["sample"]
                conn.execute(
                    """INSERT INTO reviews
                       (mandal_id, reviewer, overall, crowd, parking, comment, is_sample)
                       VALUES (?, 'Sample data', ?, ?, ?, '', 1)""",
                    (cur.lastrowid, overall, crowd, parking),
                )


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
LIST_SQL = """
SELECT m.*,
       ROUND(AVG(r.overall), 1) AS avg_overall,
       ROUND(AVG(r.crowd),   1) AS avg_crowd,
       ROUND(AVG(r.parking), 1) AS avg_parking,
       COALESCE(SUM(r.is_sample = 0), 0) AS review_count,
       (SELECT filename FROM photos p WHERE p.mandal_id = m.id
         ORDER BY p.id DESC LIMIT 1) AS cover_photo
FROM mandals m
LEFT JOIN reviews r ON r.mandal_id = m.id
{where}
GROUP BY m.id
ORDER BY m.name
"""


def get_all_mandals():
    with get_conn() as conn:
        rows = conn.execute(LIST_SQL.format(where="")).fetchall()
    return [dict(r) for r in rows]


def get_mandal(mandal_id):
    """One mandal with its recent reviews and photos, or None."""
    with get_conn() as conn:
        row = conn.execute(LIST_SQL.format(where="WHERE m.id = ?"), (mandal_id,)).fetchone()
        if row is None:
            return None
        mandal = dict(row)
        mandal["reviews"] = [dict(r) for r in conn.execute(
            """SELECT reviewer, overall, crowd, parking, comment, created_at
               FROM reviews WHERE mandal_id = ? AND is_sample = 0
               ORDER BY id DESC LIMIT 20""", (mandal_id,))]
        mandal["photos"] = [dict(r) for r in conn.execute(
            """SELECT filename, uploader FROM photos
               WHERE mandal_id = ? ORDER BY id DESC LIMIT 12""", (mandal_id,))]
    return mandal


# --------------------------------------------------------------------------
# Writing  (always use ? placeholders - never build SQL with f-strings,
# otherwise users can break or hijack your database: "SQL injection")
# --------------------------------------------------------------------------
def add_mandal(name, area, lat, lng, description="", station="", year=None):
    """Insert a mandal. Returns new id, or None if the name already exists."""
    try:
        with get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO mandals
                   (name, area, description, nearest_station, established_year,
                    lat, lng, coords_verified)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                (name, area, description, station, year, lat, lng),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:  # UNIQUE(name) violated
        return None


def add_review(mandal_id, reviewer, overall, crowd, parking, comment):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO reviews (mandal_id, reviewer, overall, crowd, parking, comment)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (mandal_id, reviewer, overall, crowd, parking, comment),
        )


def add_photo(mandal_id, filename, uploader):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO photos (mandal_id, filename, uploader) VALUES (?, ?, ?)",
            (mandal_id, filename, uploader),
        )


def mandal_exists(mandal_id):
    with get_conn() as conn:
        return conn.execute("SELECT 1 FROM mandals WHERE id = ?", (mandal_id,)).fetchone() is not None


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH} with {len(get_all_mandals())} mandals.")
