# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

class AccountAccountTemplate(models.Model):
    _inherit = 'account.account.template'

    type = fields.Char(string="Type")
    parent_id = fields.Many2one('account.account.template', string="Parent")
    shortcut = fields.Integer(string="Cod.Curto", index=True)

class AccountAccount(models.Model):
    _inherit = 'account.account'

    type = fields.Char(string="Type")
    parent_id = fields.Many2one('account.account.template', string="Parent")

