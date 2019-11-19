

def migrate(cr, version):
    # Alter table name
    if not version:
        return

    # Recalculate all payments
    sql = """SELECT move.id, move.reconciled, move.full_reconcile_id FROM account_move_line AS move 
        LEFT JOIN account_account AS account ON account.id = move.account_id 
        WHERE full_reconcile_id is not null AND account.reconcile = true;"""
    
    cr.execute(sql)
    arows = cr.fetchall()
    for arow in arows:
        sql = """SELECT move.date_maturity FROM account_move_line AS move 
            WHERE full_reconcile_id = %s AND move.id != %s
            LIMIT 1;""" % (arow[2],arow[0])
        cr.execute(sql)
        brows = cr.fetchone()
        if len(brows) > 0:
            sql = """UPDATE account_move_line SET date_maturity = '%s'
                WHERE id = %s;""" % (brows[0],arow[0])
            cr.execute(sql)
        