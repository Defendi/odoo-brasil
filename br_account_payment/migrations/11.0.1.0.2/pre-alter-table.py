

def migrate(cr, version):
    # Alter table name
    if not version:
        return

    cr.execute("ALTER TABLE account_move_line DROP COLUMN IF EXISTS payment_date;")
