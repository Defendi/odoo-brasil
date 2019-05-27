# © 2019 Mackilem Van der Laan, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_account_position_id = fields.Many2one(
        'account.fiscal.position', 
        company_dependent=True,
        string="Posicao Fiscal Venda",
        help="The fiscal position will determine taxes and accounts used for the partner.", oldname="property_account_position")

    property_purchase_fiscal_position_id = fields.Many2one(
        string="Posição Fiscal Compra",
        comodel_name="account.fiscal.position",
        domain="[('fiscal_type', '=', 'entrada')]",
        company_dependent=True,
        ondelete="set null")
