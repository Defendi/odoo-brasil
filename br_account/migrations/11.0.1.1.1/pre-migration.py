
def column_exists(cr, table, column):
    """ Check whether a certain column exists """
    cr.execute(
        'SELECT count(attname) FROM pg_attribute '
        'WHERE attrelid = '
        '( SELECT oid FROM pg_class WHERE relname = %s ) '
        'AND attname = %s',
        (table, column))
    return cr.fetchone()[0] == 1

def migrate(cr, version):

    if not version:
        return

    if not column_exists(cr, 'account_invoice', 'total_fcp'):
        cr.execute("ALTER TABLE public.account_invoice ADD COLUMN total_fcp numeric;")

    if not column_exists(cr, 'account_invoice', 'total_fcp_st'):
        cr.execute("ALTER TABLE public.account_invoice ADD COLUMN total_fcp_st numeric;")

    if not column_exists(cr, 'account_invoice', 'total_icms_valor_credito'):
        cr.execute("ALTER TABLE public.account_invoice ADD COLUMN total_icms_valor_credito numeric;")

    if not column_exists(cr, 'account_invoice_line', 'icms_base_calculo_fcp'):
        cr.execute("ALTER TABLE public.account_invoice_line ADD COLUMN icms_base_calculo_fcp numeric;")

    if not column_exists(cr, 'account_invoice_line', 'icms_valor_operacao'):
        cr.execute("ALTER TABLE public.account_invoice_line ADD COLUMN icms_valor_operacao numeric;")

    if not column_exists(cr, 'account_invoice_line', 'icms_base_calculo_fcp_st'):
        cr.execute("ALTER TABLE public.account_invoice_line ADD COLUMN icms_base_calculo_fcp_st numeric;")

