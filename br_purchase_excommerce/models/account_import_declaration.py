from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

DI_STATES= {'draft': [('readonly', False)]}

class ImportDeclaration(models.Model):
    _inherit = 'br_account.import.declaration'

    purchase_id = fields.Many2one(comodel_name='purchase.order',string='Ordem de Compra',
                                  domain="[('partner_id','=',partner_id),('state','=','purchase')]", 
                                  readonly=True, states={'draft': [('readonly', False)]})

    def _prepare_import_line_from_po_line(self, line, idx):
        if bool(line.order_id.partner_id):
            suplierinfo = self.env['product.supplierinfo'].search([('name','=',line.order_id.partner_id.id),
                                                                   ('product_tmpl_id','=',line.product_id.product_tmpl_id.id)],limit=1)
        
        price_vucv = ((line.product_qty * line.price_unit) - line.valor_desconto) / line.product_qty
        
        data = {
            'name': '001',
            'sequence_addition': str(idx+1).zfill(3),
            'origin': line.order_id.origin,
            'product_id': line.product_id.id,
            'uom_id': line.product_uom.id,
            'quantity': line.product_qty,
            'price_vucv': price_vucv,
            'discount': 0.0,
            'weight_unit': line.product_id.weight,
            'manufacturer_description': suplierinfo.product_name or line.product_id.name,
            'manufacturer_code': suplierinfo.product_code or line.product_id.default_code,
            'ipi_inclui_ii_base': True,
            'purchase_line_id': line,
        }
        return data

    
    @api.onchange('purchase_id')
    def purchase_order_change(self):
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id
        fpos = self.purchase_id.fiscal_position_id or self.partner_id.property_purchase_fiscal_position_id
        
        self.fiscal_position_id = fpos
        self.currency_purchase_id = self.purchase_id.currency_id
        self.freight_value = self.purchase_id.total_frete
        self.insurance_value = self.purchase_id.total_seguro

        new_lines = self.env['br_account.import.declaration.line']
        for idx, line in enumerate(self.purchase_id.order_line):
            data = self._prepare_import_line_from_po_line(line,idx)
            if fpos:
                product_id = self.env['product.product'].browse([data['product_id']])
                vals = fpos.map_tax_extra_values(product_id, self.partner_id, product_id.fiscal_classification_id, False, False, False)
                data['tax_ii_id'] = vals.get('tax_ii_id',False)
                data['tax_ipi_id'] = vals.get('tax_ipi_id',False)
                data['tax_pis_id'] = vals.get('tax_pis_id',False)
                data['tax_cofins_id'] = vals.get('tax_cofins_id',False)
                data['tax_icms_id'] = vals.get('tax_icms_id',False)
                data['icms_difer'] = True if vals.get('icms_aliquota_diferimento',0.0) > 0.0 else False
                data['icms_aliq_difer'] = vals.get('icms_aliquota_diferimento',0.0)
                data['tax_icms_st_id'] = vals.get('tax_icms_st_id',False)
                    
            new_line = new_lines.new(data)
            new_lines += new_line

        self.line_ids += new_lines
        return {}

    def adjust_order(self):
        self.ensure_one()
        self.purchase_id.currency_id = self.currency_id
        for line in self.line_ids:
            if line.purchase_line_id:
                line.purchase_line_id.write({
                    'price_unit': line.price_cost,
                    'valor_desconto': 0.0,
                    'outras_despesas': 0.0,
                    'valor_seguro': 0.0,
                    'valor_frete': 0.0,
                    'valor_aduana': 0.0,
                    #'taxes_id': [(5,)],
                })
        
    @api.multi
    def confirm(self):
        for di in self:
            di.adjust_order()
        super(ImportDeclaration,self).confirm()

class ImportDeclarationLine(models.Model):
    _inherit = 'br_account.import.declaration.line'
    
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Line')
