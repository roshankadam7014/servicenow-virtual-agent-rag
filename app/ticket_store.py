
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tickets.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_status_id
                ON incidents(status, id DESC)
            """)

       
        # Assign ticket numbers to any older rows that lack one.
        rows = connection.execute("""
            SELECT id FROM incidents
            WHERE ticket_number IS NULL
        """).fetchall()

        for row in rows:
            ticket_number = f"INC{row['id']:06d}"
            connection.execute("""
                UPDATE incidents
                SET ticket_number = ?
                WHERE id = ?
            """, (ticket_number, row["id"]))

        # Store conversation messages linked to support tickets.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(id)
                    ON DELETE CASCADE
            )
        """)

        
        # Record ticket status changes
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incident_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(id)
                    ON DELETE CASCADE
            )
        """)




def create_incident(
    title: str,
    description: str,
    category: str,
    priority: str = "Medium"
):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO incidents (
                title, description, category, priority,
                status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'Open', ?, ?)
        """, (
            title, description, category, priority, now, now
        ))

        incident_id = cursor.lastrowid
        ticket_number = f"INC{incident_id:06d}"

        connection.execute("""
            UPDATE incidents
            SET ticket_number = ?
            WHERE id = ?
        """, (ticket_number, incident_id))

        row = connection.execute("""
            SELECT * FROM incidents WHERE id = ?
        """, (incident_id,)).fetchone()

        return dict(row)



def list_incidents(
    limit=None,
    offset=0,
    search="",
    status="All",
    priority="All",
    category="All",
):
    query = "SELECT * FROM incidents WHERE 1=1"
    params = []

    if search:
        query += """
            AND (
                LOWER(ticket_number) LIKE ?
                OR LOWER(title) LIKE ?
            )
        """
        search_value = f"%{search.lower()}%"
        params.extend([search_value, search_value])

    if status != "All":
        query += " AND status = ?"
        params.append(status)

    if priority != "All":
        query += " AND priority = ?"
        params.append(priority)

    if category != "All":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY id DESC"

    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]



def count_incidents(
    search="",
    status="All",
    priority="All",
    category="All",
):
    query = "SELECT COUNT(*) AS total FROM incidents WHERE 1=1"
    params = []

    if search:
        query += """
            AND (
                LOWER(ticket_number) LIKE ?
                OR LOWER(title) LIKE ?
            )
        """
        search_value = f"%{search.lower()}%"
        params.extend([search_value, search_value])

    if status != "All":
        query += " AND status = ?"
        params.append(status)

    if priority != "All":
        query += " AND priority = ?"
        params.append(priority)

    if category != "All":
        query += " AND category = ?"
        params.append(category)

    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
        return row["total"]




def get_incident(ticket_number: str):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT * FROM incidents
            WHERE ticket_number = ?
        """, (ticket_number.upper(),)).fetchone()

        return dict(row) if row else None




def update_incident(ticket_number: str, status: str):
    now = datetime.now(timezone.utc).isoformat()

    allowed_transitions = {
        "Open": {"In Progress"},
        "In Progress": {"Resolved"},
        "Resolved": {"Closed", "In Progress"},
        "Closed": set(),
    }

    with get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        row = connection.execute("""
            SELECT id, status
            FROM incidents
            WHERE ticket_number = ?
        """, (ticket_number.upper(),)).fetchone()

        if row is None:
            return None

        old_status = row["status"]

        # Allow an unchanged status without recording a new transition.
        if old_status == status:
            updated = connection.execute("""
                SELECT * FROM incidents WHERE id = ?
            """, (row["id"],)).fetchone()
            return dict(updated)

        # Reject transitions that are not allowed.
        if status not in allowed_transitions.get(old_status, set()):
            raise ValueError(
                f"Cannot change ticket status from "
                f"'{old_status}' to '{status}'."
            )

        # Record the valid status transition.
        connection.execute("""
            INSERT INTO incident_status_history (
                incident_id, old_status, new_status, changed_at
            )
            VALUES (?, ?, ?, ?)
        """, (row["id"], old_status, status, now))

        # Update the ticket only after validation succeeds.
        connection.execute("""
            UPDATE incidents
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (status, now, row["id"]))

        updated = connection.execute("""
            SELECT * FROM incidents WHERE id = ?
        """, (row["id"],)).fetchone()

        return dict(updated)


    
def save_conversation(
    ticket_number: str,
    user_message: str,
    assistant_response: str,
):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        incident = connection.execute(
            """
            SELECT id FROM incidents
            WHERE ticket_number = ?
            """,
            (ticket_number.upper(),),
        ).fetchone()

        if incident is None:
            return None

        connection.execute(
            """
            INSERT INTO conversation_history (
                incident_id,
                user_message,
                assistant_response,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                incident["id"],
                user_message,
                assistant_response,
                now,
            ),
        )

    return True


def get_conversation_history(ticket_number: str):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                ch.user_message,
                ch.assistant_response,
                ch.created_at
            FROM conversation_history ch
            JOIN incidents i ON i.id = ch.incident_id
            WHERE i.ticket_number = ?
            ORDER BY ch.id ASC
            """,
            (ticket_number.upper(),),
        ).fetchall()

        return [dict(row) for row in rows]


def get_status_history(ticket_number: str):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                h.old_status,
                h.new_status,
                h.changed_at
            FROM incident_status_history h
            JOIN incidents i ON i.id = h.incident_id
            WHERE i.ticket_number = ?
            ORDER BY h.id ASC
        """, (ticket_number.upper(),)).fetchall()

        return [dict(row) for row in rows]


