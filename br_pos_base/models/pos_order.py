# -*- coding: utf-8 -*-

from openerp import models, fields, api
   
class PosOrder(models.Model):
    _inherit = 'pos.order'

    cnpj_cpf = fields.Char('CNPJ/CPF', size=18, copy=False, default='Não Indicado')
    
    def _action_create_invoice_line(self, line=False, invoice_id=False):
        res = super(PosOrder,self)._action_create_invoice_line(line=line, invoice_id=invoice_id)
        if len(res.product_id) > 0:
            res.write({'fiscal_classification_id': res.product_id.fiscal_classification_id.id or False})
        return res
