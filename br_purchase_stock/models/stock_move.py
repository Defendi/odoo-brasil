# -*- coding: utf-8 -*-

from odoo import api, fields, models

class StockMove(models.Model):
    _inherit = 'stock.move'

    category_id         = fields.Many2one('product.category', string="Categoria", related="product_id.product_tmpl_id.categ_id", store=True)
    account_analytic_id = fields.Many2one('account.analytic.account', string="Centro de Custos", related="purchase_line_id.account_analytic_id", store=True)
    analytic_tag_ids    = fields.Many2many(string='Rótulos Custo', related="purchase_line_id.analytic_tag_ids")
    total               = fields.Float(string="Valor Total", compute="_calcula_total", store=True)
    
    def _calcula_total(self):
        for move in self:
            move.total = move.price_unit * move.product_qty
        return True