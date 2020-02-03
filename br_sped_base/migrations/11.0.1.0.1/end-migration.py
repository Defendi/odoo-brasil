# Alexandre Defendi - 2020

def migrate(cr, version):
    # Alter table name
    if not version:
        return
    import logging
    from odoo.tools import convert_file

    _logger = logging.getLogger(__name__)
    
    _logger.info('>>> Iniciando ')
    filename = 'data/product_uom.csv'
    convert_file(cr, 'br_sped_base', filename, None, mode='init', noupdate=False, kind='init', report=None)
