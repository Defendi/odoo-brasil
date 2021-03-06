# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountAccountTemplate(models.Model):
    _inherit = 'account.account.template'

    account_type = fields.Selection([('tax', 'Imposto'), ('income', 'Receita'), ('expense', 'Despesa')],string="Tipo de conta")
    shortcut = fields.Integer(string="Cod.Curto", index=True)

class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_type = fields.Selection([('tax', 'Imposto'), ('income', 'Receita'), ('expense', 'Despesa')],string="Tipo de conta")
    shortcut = fields.Integer(string="Cod.Curto", index=True)

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    indPag = fields.Selection(
        [('0', 'Pagamento à Vista'), ('1', 'Pagamento à Prazo')],
        'Indicador de Pagamento', default='0')
