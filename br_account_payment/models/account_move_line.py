import datetime

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.multi
    @api.depends('debit', 'credit', 'user_type_id', 'amount_residual')
    def _compute_payment_value(self):
        for item in self:
            item.payment_value = item.debit if item.user_type_id.type == 'receivable' else item.credit * -1
            item.payment_date = None
            if item.reconciled and len(item.full_reconcile_id) > 0:
                data = False
                for line_pag in item.full_reconcile_id.reconciled_line_ids:
                    if line_pag.id != item.id:
                        data = datetime.datetime.strptime(line_pag.date_maturity[:10], "%Y-%m-%d")
                        break
                if bool(data):
                    item.payment_date = data.strftime('%d/%m/%Y')
                
    payment_value = fields.Monetary(string="Valor", compute=_compute_payment_value, store=True,currency_field='company_currency_id')
    payment_date = fields.Char(string="Pago em", size=12, compute=_compute_payment_value, store=True, index=True)
    payment_mode_id = fields.Many2one('l10n_br.payment.mode', string=u"Modo de pagamento")
    l10n_br_order_line_id = fields.Many2one('payment.order.line', string='Linha de Pagamento')

    @api.multi
    def action_register_payment(self):
        dummy, act_id = self.env['ir.model.data'].get_object_reference(
            'account', 'action_account_invoice_payment')
        receivable = (self.user_type_id.type == 'receivable')
        vals = self.env['ir.actions.act_window'].browse(act_id).read()[0]
        vals['context'] = {
            'default_amount': abs(self.amount_residual),#self.debit or self.credit,
            'default_partner_type': 'customer' if receivable else 'supplier',
            'default_partner_id': self.partner_id.id,
            'default_communication': self.name,
            'default_payment_type': 'inbound' if receivable else 'outbound',
            'default_move_line_id': self.id,
        }
        if self.invoice_id:
            vals['context']['default_invoice_ids'] = [self.invoice_id.id]
        return vals
