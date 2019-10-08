from odoo import models, fields, api
from .cst import ORIGEM_PROD

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fiscal_type = fields.Selection(
        [('service', 'Serviço'), ('product', 'Produto')], 'Tipo Fiscal',
        required=True, default='product')

    origin = fields.Selection(ORIGEM_PROD, 'Origem', default='0')
    fiscal_classification_id = fields.Many2one(
        'product.fiscal.classification', string="Classificação Fiscal (NCM)")
    service_type_id = fields.Many2one(
        'br_account.service.type', 'Tipo de Serviço')
    cest = fields.Char(string="CEST", size=10,
                       help="Código Especificador da Substituição Tributária")
    fiscal_observation_ids = fields.Many2many(
        'br_account.fiscal.observation', string="Mensagens Doc. Eletrônico")
    fiscal_category_id = fields.Many2one(
        'br_account.fiscal.category',
        string='Categoria Fiscal')

    @api.onchange('type')
    def onchange_product_type(self):
        self.fiscal_type = 'service' if self.type == 'service' else 'product'

    @api.onchange('fiscal_type')
    def onchange_product_fiscal_type(self):
        self.type = 'service' if self.fiscal_type == 'service' else 'cons'
