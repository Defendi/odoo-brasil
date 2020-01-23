from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    boleto_emitido = fields.Boolean(string="Emitido")
    nosso_numero = fields.Char(string="Nosso Número", size=30)
    boleto_date = fields.Date(string='Data Emissão')
    boleto = fields.Boolean(related="payment_mode_id.boleto")

    @api.multi
    def unlink(self):
        for item in self:
            line_ids = self.env['payment.order.line'].search(
                [('move_line_id', '=', item.id),
                 ('state', '=', 'draft')])
            line_ids.sudo().unlink()
        return super(AccountMoveLine, self).unlink()

    @api.multi
    def _update_check(self):
        for item in self:
            total = self.env['payment.order.line'].search_count(
                [('move_line_id', '=', item.id),
                 ('type', '=', 'receivable'),
                 ('state', 'not in', ('draft', 'cancelled', 'rejected'))])
            if total > 0:
                raise UserError(_('Existem boletos emitidos para esta fatura!\
                                  Cancele estes boletos primeiro'))
        return super(AccountMoveLine, self)._update_check()

    @api.multi
    def action_print_boleto(self):
        if self.move_id.state in ('draft', 'cancel'):
            raise UserError(
                _('Fatura provisória ou cancelada não permite emitir boleto'))
        self = self.with_context({'origin_model': 'account.invoice'})
        return self.env.ref(
            'br_boleto.action_boleto_account_invoice').report_action(self)

    @api.multi
    def open_wizard_print_boleto(self):
        return({
            'name': 'Alterar / Reimprimir Boleto',
            'type': 'ir.actions.act_window',
            'res_model': 'br.boleto.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'origin_model': 'account.move.line',
                'default_move_line_id': self.id,
            }
        })

    def verifica_sacado(self):
        res = []
        if self.partner_id:
            sacado = self.partner_id
            if not sacado.street:
                res.append("Indique a rua.")
            if not sacado.number:
                res.append("Indique o número.")
            if not sacado.city_id:
                res.append("Indique a cidade.")
            if not sacado.state_id:
                res.append("Indique o Estado.")
            if sacado.company_type == 'company':
                if not sacado.legal_name:
                    res.append("Indique a Razão Social.")
                if not sacado.cnpj_cpf:
                    res.append("Indique o CNPJ da empresa.")
            else:
                if not sacado.name:
                    res.append("Indique o Nome.")
                if not sacado.cnpj_cpf:
                    res.append("Indique o CPF da pessoa.")
        else:
            res.append(u"Indique o sacado.")
        return res

