import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    import_id = fields.Many2one(comodel_name='br_account.import.declaration',string='Declaração Importação', readonly=True, states={'draft': [('readonly', False)]})

    def _prepare_invoice_line_from_di_line(self, line_id):
        invoice_line = self.env['account.invoice.line']
        line = self.env['br_account.import.declaration.line'].browse([line_id])
        data = {
            'name': line.product_id.name,
            'origin': line.import_declaration_id.name,
            'uom_id': line.uom_id.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context({'journal_id': self.journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': line.price_unit_edoc,
            'quantity': line.quantity,
            'discount': 0.0,
            'outras_despesas': line.pis_valor + line.cofins_valor + line.siscomex_value,
            'icms_base_calculo_manual': line.icms_base_calculo,
            'tax_icms_id': line.tax_icms_id.id,
            'ipi_base_calculo_manual': line.ipi_base_calculo,
            'tax_ipi_id': line.tax_ipi_id.id,
            'pis_base_calculo_manual': line.pis_base_calculo,
            'tax_pis_id': line.tax_pis_id.id,
            'cofins_base_calculo_manual': line.cofins_base_calculo,
            'tax_cofins_id': line.tax_cofins_id.id,
            'ii_base_calculo': line.ii_base_calculo,
            'tax_ii_id': line.tax_ii_id.id,
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, False, self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data

    @api.onchange('import_id')
    def import_change(self):
        if not self.import_id:
            return {}
        self.env.context = dict(self.env.context, from_import_order_change=True)
        self.type = 'out_invoice'
        self.partner_id = self.import_id.partner_id.id

        new_line = []
        new_line.append((5,))
        for line in self.import_id.line_ids:
            data = self._prepare_invoice_line_from_di_line(line.id)
            new_line.append((0, 0, data))
        self.invoice_line_ids = new_line
        self.fiscal_position_id = self.import_id.fiscal_position_id.id

    @api.onchange('fiscal_position_id')
    def _onchange_br_account_fiscal_position_id(self):
        if not self.env.context.get('from_import_order_change', False):
            super(AccountInvoice,self)._onchange_br_account_fiscal_position_id()
        self.env.context = dict(self.env.context, from_import_order_change=False)

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        if not self.env.context.get('from_import_order_change', False):
            super(AccountInvoice,self)._onchange_partner_id()
            
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

