# © 2019 Raphael Rodrigues, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError

class PaymentAccountMoveLine(models.TransientModel):
    _name = 'payment.account.move.line'
    _description = 'Assistente Para Lançamento de Pagamentos'

    @api.one
    @api.depends('payment_date')
    def _late_payment(self):
        if self.payment_date < self.move_line_id.date_maturity:
            self.late_payment = 0
        else:
            d1 = datetime.strptime(self.move_line_id.date_maturity, "%Y-%m-%d")
            d2 = datetime.strptime(self.payment_date, "%Y-%m-%d")
            self.late_payment = (d2 - d1).days
    
    @api.one
    @api.depends('fee','interest','principal','discount')
    def _pay_amount(self):
        self.pay_sub = (self.principal + self.discount)
        self.pay_amount = self.principal + self.fee + self.interest
            
    company_id = fields.Many2one(
        'res.company', related='journal_id.company_id',
        string='Exmpresa', readonly=True
    )
    move_line_id = fields.Many2one(
        'account.move.line', readonly=True, string='Conta à Pagar/Receber')
    date_maturity = fields.Date(related='move_line_id.date_maturity',string='Vencimento',readonly=True)
    
    invoice_id = fields.Many2one(
        'account.invoice', readonly=True, string='Fatura')
    partner_type = fields.Selection(
        [('customer', 'Cliente'), ('supplier', 'Fornecedor')], readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Cliente/Fornecedor', readonly=True
    )
    journal_id = fields.Many2one(
        'account.journal', string="Diário", required=True,
        domain=[('type', 'in', ('bank', 'cash', 'general'))]
    )
    communication = fields.Char(string='Anotações')
    payment_date = fields.Date(
        string='Data do Pagamento',
        default=fields.Date.context_today, required=True
    )
    currency_id = fields.Many2one(
        'res.currency', string='Moeda', required=True,
        default=lambda self: self.env.user.company_id.currency_id
    )
    amount_residual = fields.Monetary(
        string='Saldo', readonly=True,
        related='move_line_id.amount_residual',
        currency_field='currency_id'
    )

    principal = fields.Monetary(string='Principal', required=True, oldname='amount', default=0.0, currency_field='currency_id')
    discount = fields.Monetary(string='Desconto (-)', required=True, default=0.0, currency_field='currency_id')
    pay_sub = fields.Monetary(compute="_pay_amount",string='Valor Pago', currency_field='currency_id', readonly=True, store=True)
    interest = fields.Monetary(string='Juros (+)', required=True, default=0.0, currency_field='currency_id')
    fee = fields.Monetary(string='Multa (+)', required=True, default=0.0, currency_field='currency_id')
    
    pay_amount = fields.Monetary(compute="_pay_amount",string='Total Pago', currency_field='currency_id', readonly=True, store=True)
    late_payment = fields.Integer(compute="_late_payment",string="Dia(s) atraso")

    @api.model
    def default_get(self, fields):
        rec = super(PaymentAccountMoveLine, self).default_get(fields)
        move_line_id = rec.get('move_line_id', False)
        principal = 0
        if not move_line_id:
            raise UserError(
                _("Não foi selecionada nenhuma linha de cobrança."))
        move_line = self.env['account.move.line'].browse(move_line_id)
        if move_line[0].amount_residual:
            principal = move_line[0].amount_residual if \
                rec['partner_type'] == 'customer' else \
                move_line[0].amount_residual * -1
#         if move_line[0].invoice_id:
#             invoice = move_line[0].invoice_id
#         else:
#             raise UserError(_("A linha de cobrança selecionada não possui nenhuma fatura relacionada."))
        rec.update({
            'principal': principal,
            'invoice_id': move_line[0].invoice_id.id,
        })
        return rec

    @api.onchange('principal','discount')
    def validate_amount_payment(self):
        """
        Method used to validate the payment amount to be recorded
        :return:
        """
        real_amount_residual = self.amount_residual if \
            self.partner_type == 'customer' else \
            self.amount_residual * -1
        if self.principal + self.discount > real_amount_residual:
            raise ValidationError(_(
                'O valor do pagamento não pode ser maior '
                'que o valor da parcela.'))

    @api.onchange('payment_date')
    def _calc_late_fee_interest(self):
        if len(self.move_line_id) > 0 and self.payment_date > self.move_line_id.date_maturity:
            real_amount_residual = self.amount_residual if \
                self.partner_type == 'customer' else \
                self.amount_residual * -1
            d1 = datetime.strptime(self.move_line_id.date_maturity, "%Y-%m-%d")
            d2 = datetime.strptime(self.payment_date, "%Y-%m-%d")
            dias = (d2 - d1).days
            self.fee = real_amount_residual * (self.move_line_id.payment_mode_id.late_payment_fee / 100)
            self.interest = (((real_amount_residual * self.move_line_id.payment_mode_id.late_payment_interest) / 30)* dias) /100


    def _get_payment_vals(self):
        """
        Method responsible for generating payment record amounts
        """
        payment_type = 'inbound' if self.move_line_id.debit else 'outbound'
        payment_methods = \
            payment_type == 'inbound' and \
            self.journal_id.inbound_payment_method_ids or \
            self.journal_id.outbound_payment_method_ids
        payment_method_id = payment_methods and payment_methods[0] or False
        vals = {
            'partner_id': self.partner_id.id,
            'move_line_id': self.move_line_id.id,
            'journal_id': self.journal_id.id,
            'communication': self.communication,
            'amount': self.principal,
            'discount': self.discount,
            'interest': self.interest,
            'fee': self.fee,
            'payment_date': self.payment_date,
            'payment_type': payment_type,
            'payment_method_id': payment_method_id.id if bool(payment_method_id) else False,
            'currency_id': self.currency_id.id,
        }
        if len(self.invoice_id) > 0:
            vals['invoice_ids'] = [(6, 0, [self.invoice_id.id])]
        return vals

    def action_confirm_payment(self):
        """
        Method responsible for creating the payment
        """
        payment = self.env['account.payment']
        vals = self._get_payment_vals()
        pay = payment.create(vals)
        pay.post()
        if not self.move_line_id.invoice_id:        
            move_ids = self.move_line_id
            for move in pay.move_line_ids:
                if move.account_id.reconcile and not move.reconciled:
                    move_ids += move
            if len(move_ids) > 1:
                move_ids.reconcile() 
        