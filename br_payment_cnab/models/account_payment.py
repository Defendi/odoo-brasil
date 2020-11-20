import logging
from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class account_payment(models.Model):
    _inherit = "account.payment"

    @api.one
    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id')
    def _compute_payment_difference(self):
        if len(self.invoice_ids) == 0:
            return
        if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
            self.payment_difference = self.amount - self._compute_total_invoices_amount()
        else:
            self.payment_difference = self._compute_total_invoices_amount() - self.amount
        
        self.payment_difference += (self.fee + self.interest)
    
    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_fee = self.fee + self.interest
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
        if amount < 0.0:
            pdebit = 0.0
            pcredit = (amount + aml_fee) * (-1)
        else:
            pdebit = (amount - aml_fee)
            pcredit = 0.0

        
        move = self.env['account.move'].create(self._get_move_vals())
        
        company = self.company_id or self.env.user.company_id

        if self.discount > 0.0:
            if amount < 0.0:
                if bool(company.out_discount_account_id):
                    discount_aml_dict = self._get_shared_move_line_vals(self.discount, 0.0, amount_currency, move.id, False)
                    discount_aml_dict.update({'name': 'Desconto %s' % self.name,
                                              'account_id': company.out_discount_account_id.id,
                                              'currency_id': currency_id,
                                              'company_id': company.id})
                    discount_aml = aml_obj.create(discount_aml_dict)
                    credit = credit - self.discount
            else:
                if bool(company.in_discount_account_id):
                    discount_aml_dict = self._get_shared_move_line_vals(0.0, self.discount, amount_currency, move.id, False)
                    discount_aml_dict.update({'name': 'Desconto %s' % self.name,
                                              'account_id': company.in_discount_account_id.id,
                                              'currency_id': currency_id})
                    discount_aml = aml_obj.create(discount_aml_dict)
                    debit = debit - self.discount

        
        if aml_fee > 0.0:
            if amount < 0.0:
                if bool(company.l10n_br_interest_account_id):
                    fee_aml_dict = self._get_shared_move_line_vals(0.0, aml_fee, amount_currency, move.id, False)
                    fee_aml_dict.update({'name': 'Multa/Juros %s' % self.name,
                                         'account_id': company.l10n_br_interest_account_id.id,
                                         'currency_id': currency_id,
                                         'company_id': company.id})
                    fee_aml = aml_obj.create(fee_aml_dict)
            else:
                if bool(company.l10n_br_payment_interest_account_id):
                    fee_aml_dict = self._get_shared_move_line_vals(aml_fee, 0.0, amount_currency, move.id, False)
                    fee_aml_dict.update({'name': 'Multa/Juros %s' % self.name,
                                         'account_id': company.l10n_br_payment_interest_account_id.id,
                                         'currency_id': currency_id,
                                         'company_id': company.id})
                    fee_aml = aml_obj.create(fee_aml_dict)
                
        #Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(pdebit, pcredit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id, 'company_id': company.id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        #Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(self.payment_difference, self.currency_id, self.company_id.currency_id)
            writeoff_line['name'] = self.writeoff_label
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo

        #Write counterpart lines
        if not self.currency_id.is_zero(self.amount):
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
            liquidity_aml_dict.update({'company_id': company.id})
            aml_obj.create(liquidity_aml_dict)

#         _logger.info('nome; credito; debito; saldo')
#         for line_move in move.line_ids:
#             _logger.info('%s; %s; %s' % (line_move.name,str(line_move.credit),str(line_move.debit)))            
        #validate the payment
        move.post()

        #reconcile the invoice receivable/payable line(s) with the payment
        self.invoice_ids.register_payment(counterpart_aml)

        return move

