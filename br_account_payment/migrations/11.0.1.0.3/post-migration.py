import logging

_logger = logging.getLogger(__name__)

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
    tot = len(arows)
    pct_at = 0.0
    _logger.info('Getting started ...')
    for idx, arow in enumerate(arows):
        pct_cl = round((idx/tot)*100,0)
        if pct_at != pct_cl:
            pct_at = pct_cl
            _logger.info('....... %s percent completed' % pct_at)
        sql = """SELECT move.date_maturity FROM account_move_line AS move 
            WHERE full_reconcile_id = %s AND move.id != %s
            LIMIT 1;""" % (arow[2],arow[0])
        cr.execute(sql)
        brows = cr.fetchone()
        if len(brows) > 0:
            
            sql = """UPDATE account_move_line SET payment_date = '%s'
                WHERE id = %s;""" % (brows[0],arow[0])
            cr.execute(sql)
        