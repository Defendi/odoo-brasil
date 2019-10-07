# 11.0.0.1 - 09/2019 - Versão Inicial Alexandre Defendi

# Other imports
import re
import logging
import operator

# Odoo Imports 
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

# Checked Imports
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"
 
    default_code = fields.Char('Internal Reference', compute='_compute_default_code',inverse='_set_default_code', store=True)
   
    @api.multi
    @api.constrains('default_code')
    def _check_default_code(self):
        for prod in self:
            if bool(prod.default_code):
                vl_cod = re.sub('[0-9a-zA-Z]','',prod.default_code)
                if len(vl_cod) > 0:
                    raise ValidationError('A referência interna do produto não é válida.\nSomente números e alfanuméricos, sem espaços, podem ser usados')
                outro = self.search([('default_code','=',self.default_code),('id','!=',self.id)])
                if len(outro) > 0:
                    raise ValidationError('A referência interna de produto já foi usado em outro modelo de produto')
        
    

