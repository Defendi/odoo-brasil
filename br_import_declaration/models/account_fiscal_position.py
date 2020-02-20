
from odoo import api, fields, models

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    fiscal_type = fields.Selection(selection_add=[('import', 'Entrada Importação'),
                                                  ('export', 'Saída Importação')])