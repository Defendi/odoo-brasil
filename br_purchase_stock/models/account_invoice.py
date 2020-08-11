# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields
from odoo.addons import decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _prepare_invoice_line_from_po_line(self, line):
        res = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(
            line)
        res['valor_seguro'] = line.valor_seguro
        res['outras_despesas'] = line.outras_despesas
        res['valor_frete'] = line.valor_frete
        res['ii_valor_despesas'] = line.valor_aduana
        return res

