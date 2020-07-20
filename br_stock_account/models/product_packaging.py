# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    weight = fields.Float(string='Peso Embalagem', help="O peso da embalagem em Kg.", digits=(12,3))