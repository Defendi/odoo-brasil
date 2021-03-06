# © 2018 Johny Chen Jy <johnychenjy@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class AccountVoucherLine(models.Model):
    _inherit = 'account.voucher.line'

    analytic_tag_ids = fields.Many2many('account.analytic.tag',
                                        string='Analytic Tags')

    @api.multi
    def product_id_change(self, product_id, partner_id=False, price_unit=False, company_id=None, currency_id=None, type=None):
        res = super(AccountVoucherLine,self).product_id_change(product_id, partner_id, price_unit, company_id, currency_id, type)
        if len(self.account_id) > 0 or res['value'].get('account_id') == False:
            res['value'].pop('account_id')
        return res

    @api.model
    def _get_account(self, product, fpos, type):
        account = None
        product_accounts = product.product_tmpl_id.get_product_accounts(fpos)
        journal_id = self.voucher_id.journal_id
        
        if type == 'sale':
            account = journal_id.default_credit_account_id
            if not account:
                account = product_accounts['income']
        else:
            account = journal_id.default_debit_account_id
            if not account:
                account = product_accounts['expense']

        return account
       