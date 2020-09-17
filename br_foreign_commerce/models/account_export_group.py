# © 2020 Cristiano Rodrigues, Nexux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp

class AccountExportGroup(models.Model):
    _name = 'account.export.group'
    _description = """Grupo de Exportação"""

    number_draw = fields.Char(
        string='Nº concessório de Drawback', size=11,
        help="O número do Ato Concessório de Suspensão deve ser preenchido com 11 dígitos (AAAANNNNNND)"
        "e o número do Ato Concessório de Drawback Isenção deve ser preenchido com 9 dígitos (AANNNNNND)."
        "(Observação incluída na NT 2013/005 v. 1.10)")
    number_reg = fields.Char(
        string='Nº Registro de Exportação', size=12)
    key_nfe = fields.Char(
        string='Chave de Acesso da NF-e rec. p/ exportação', size=44,
        help="NF-e recebida com fim específico de exportação. No caso de operação com CFOP 3.503,"
        "informar a chave de acesso da NF-e que efetivou a exportação")
    qty_export = fields.Float(
        string='Quant. do item realmente exportado', digits=dp.get_precision('Product Unit of Measure'))

    account_inv_line_id = fields.Many2one('account.invoice.line',
                                          'Linha de Documento Fiscal',
                                          ondelete='cascade', index=True)

    @api.onchange("number_draw")
    def _onchange_number_draw(self):
        res = {}
        if self.number_draw:
            clear_value = re.sub('[^0-9\.]', '', self.number_draw).split('.')
            self.number_draw = clear_value[0]

        return res

    @api.onchange("number_reg")
    def _onchange_number_reg(self):
        res = {}
        if self.number_reg:
            clear_value = re.sub('[^0-9\.]', '', self.number_reg).split('.')
            self.number_reg = clear_value[0]

        return res

    @api.onchange("key_nfe")
    def _onchange_key_nfe(self):
        if self.key_nfe:
            clear_value = re.sub('[^0-9\.]', '', self.key_nfe).split('.')
            self.key_nfe = clear_value[0]
