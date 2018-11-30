

def migrate(cr, version):
    # Alter table name
    if not version:
        return

    cr.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' and table_name = 'payment_mode';")
    if cr.fetchone():
        cr.execute('ALTER TABLE payment_mode RENAME TO l10n_br_payment_mode;')
        cr.execute('ALTER SEQUENCE payment_mode_id_seq \
                   RENAME TO l10n_br_payment_mode_id_seq;')
