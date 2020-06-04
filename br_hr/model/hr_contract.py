from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

class Contract(models.Model):
    _inherit = 'hr.contract'
