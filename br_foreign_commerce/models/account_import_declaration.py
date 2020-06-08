from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

class ImportDeclaration(models.Model):
    _inherit = 'br_account.import.declaration'

    @api.depends('line_ids')
    def _compute_di(self):
        for di in self:
            total_fob_vl = sum(line.amount_value for line in di.line_ids)
            total_fob_lc = sum(line.amount_value_cl for line in di.line_ids)
            total_weight = sum((line.weight_unit * line.quantity) for line in di.line_ids)
            total_cif = sum(line.cif_value for line in di.line_ids)
            total_cif_afrmm = sum(line.cif_afrmm_value for line in di.line_ids)
            vals = {
                'total_weight': total_weight,
                'total_fob_vl': total_fob_vl,
                'total_fob_lc': total_fob_lc,
                'total_cif': total_cif,
                'total_cif_afrmm': total_cif_afrmm,
            }
            di.update(vals)

    @api.depends('tax_cambial','freight_converted_vl','insurance_converted_vl','afrmm_converted_vl','siscomex_converted_vl')
    def _compute_desembaraco(self):
        for di in self:
            di.total_desembaraco_vl = (di.freight_converted_vl + di.insurance_converted_vl + di.afrmm_value + di.siscomex_value)

    @api.depends('freight_value')
    def _compute_freight(self):
        for di in self:
            di.freight_converted_vl = di.freight_value * di.tax_cambial

    @api.depends('insurance_value')
    def _compute_insurance(self):
        for di in self:
            di.insurance_converted_vl = di.insurance_value * di.tax_cambial

    @api.depends('afrmm_value')
    def _compute_afrmm(self):
        for di in self:
            di.afrmm_converted_vl = di.afrmm_value

    @api.depends('siscomex_value')
    def _compute_siscomex(self):
        for di in self:
            di.siscomex_converted_vl = di.siscomex_value

    partner_id = fields.Many2one('res.partner', string='Exportador')
    freight_value = fields.Float('Valor Frete', digits=dp.get_precision('Account'), default=0.00)
    insurance_value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00)
    tax_cambial = fields.Float('Tx. Cambial', digits=(12,6), default=0.00)
    
    invoice_id = fields.Many2one('account.invoice', 'Fatura', ondelete='cascade', index=True)
    name = fields.Char('Número da DI', size=10, required=True)
    date_registration = fields.Date('Data de Registro', required=True)
    state_id = fields.Many2one('res.country.state', 'Estado',domain="[('country_id.code', '=', 'BR')]", required=True)
    location = fields.Char('Local', required=True, size=60)
    date_release = fields.Date('Data de Liberação', required=True)
    type_transportation = fields.Selection([
        ('1', '1 - Marítima'),
        ('2', '2 - Fluvial'),
        ('3', '3 - Lacustre'),
        ('4', '4 - Aérea'),
        ('5', '5 - Postal'),
        ('6', '6 - Ferroviária'),
        ('7', '7 - Rodoviária'),
        ('8', '8 - Conduto / Rede Transmissão'),
        ('9', '9 - Meios Próprios'),
        ('10', '10 - Entrada / Saída ficta'),
    ], 'Transporte Internacional', required=True, default="1")
    type_import = fields.Selection([
        ('1', '1 - Importação por conta própria'),
        ('2', '2 - Importação por conta e ordem'),
        ('3', '3 - Importação por encomenda'),
    ], 'Tipo de Importação', default='1', required=True)
    thirdparty_cnpj = fields.Char('CNPJ', size=18)
    thirdparty_state_id = fields.Many2one('res.country.state', 'Estado',domain="[('country_id.code', '=', 'BR')]")
    exporting_code = fields.Char('Código do Exportador', required=True, size=60)
    additional_information = fields.Text('Informações Adicionais')

    company_id = fields.Many2one('res.company', 'Empresa', default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Moeda Empresa", readonly=True)
    currency_purchase_id = fields.Many2one('res.currency', string="Moeda Compra", required=True, default=lambda self: self.env.user.company_id.currency_id.id)

    afrmm_value = fields.Float('Valor AFRMM', digits=dp.get_precision('Account'), default=0.00)
    siscomex_value = fields.Float('Valor SISCOMEX', digits=dp.get_precision('Account'), default=0.00)
    freight_value = fields.Float('Valor Frete', digits=dp.get_precision('Account'), default=0.00)
    insurance_value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00)
    tax_cambial = fields.Float('Taxa Cambial', digits=(12,6), default=0.00)
    
    line_ids = fields.One2many('br_account.import.declaration.line','import_declaration_id', 'Linhas da DI')

    # Campos Calculados
    freight_converted_vl = fields.Float('Frete', compute='_compute_freight', digits=dp.get_precision('Account'), readonly=True, store=True)
    insurance_converted_vl = fields.Float('Seguro', compute='_compute_insurance', digits=dp.get_precision('Account'), readonly=True, store=True)
    afrmm_converted_vl = fields.Float('AFRMM', compute='_compute_afrmm', digits=dp.get_precision('Account'), readonly=True, store=True)
    siscomex_converted_vl = fields.Float('SISCOMEX', compute='_compute_siscomex', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_desembaraco_vl = fields.Float('Total Desembaraço', compute='_compute_desembaraco', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_weight = fields.Float('Peso Liq.', compute='_compute_di', digits=(12,4), readonly=True, store=True)
    total_fob_vl = fields.Float('Total FOB', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_fob_lc = fields.Float('Total FOB', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_cif = fields.Float(string='Total CIF', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_cif_afrmm = fields.Float(string='Total CIF+AFRMM', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)

class ImportDeclarationLine(models.Model):
    _inherit = 'br_account.import.declaration.line'
    _order = 'import_declaration_id, name, sequence_addition, id'

    @api.depends('quantity','price_unit','amount_discount','weight_unit','freight_converted_vl','afrmm_converted_vl','siscomex_converted_vl',
                 'insurance_converted_vl')
    def _compute_item(self):
        for line in self:
            amount = (line.quantity * line.price_unit) - line.amount_discount
            amount_local = amount * line.tax_cambial
            price_unit_local = amount_local / line.quantity if line.quantity > 0.0 else 0.0
            weight = line.weight_unit * line.quantity
            
            freight_p = (weight / line.total_weight) * 100 if line.total_weight > 0.0 else 0.0
            freight_value = line.freight_converted_vl * (freight_p / 100)

            insurance_part = (amount / line.total_fob_vl) * 100 if line.total_fob_vl > 0.0 else 0.0
            insurance_value = line.insurance_converted_vl * (insurance_part / 100)
            afrmm_value = line.afrmm_converted_vl * (insurance_part / 100)

            cif_value = amount_local + freight_value + insurance_value
            cif_afrmm_value = cif_value + afrmm_value
            
            siscomex_part = (cif_value / line.total_cif) * 100 if line.total_cif > 0.0 else 0.0
            siscomex_value = line.siscomex_converted_vl * (siscomex_part / 100)
            
            vals = {
                'amount_value': amount, 
                'amount_value_cl': amount_local,
                'price_unit_cl': price_unit_local,
                'amount_weight': weight,
                'freight_part': freight_p,
                'freight_value': freight_value,
                'insurance_part': insurance_part,
                'insurance_value': insurance_value,
                'afrmm_value': afrmm_value,
                'cif_value': cif_value,
                'cif_afrmm_value': cif_afrmm_value,
                'siscomex_part': siscomex_part,
                'siscomex_value': siscomex_value,
            }
            line.update(vals)

    @api.depends('cif_afrmm_value','tax_ii_id')
    def _compute_ii(self):
        for line in self:
            ii_base_calculo = line.cif_afrmm_value
            ii_aliquota = 0.0
            ii_valor = 0.0
            if bool(line.tax_ii_id):
                ii_aliquota += line.tax_ii_id.amount
                ii_valor += ii_base_calculo * (ii_aliquota/100)
            line.update({
                'ii_base_calculo': ii_base_calculo,
                'ii_aliquota': ii_aliquota,
                'ii_valor': ii_valor,
            })
                 
    import_declaration_id = fields.Many2one('br_account.import.declaration', 'DI', ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='import_declaration_id.currency_id', readonly=True, store=True)
    currency_purchase_id = fields.Many2one('res.currency', related='import_declaration_id.currency_purchase_id', readonly=True, store=True)
    tax_cambial = fields.Float(related='import_declaration_id.tax_cambial', readonly=True, store=True)
    total_weight = fields.Float(related='import_declaration_id.total_weight', readonly=True, store=True)
    freight_converted_vl = fields.Float(related='import_declaration_id.freight_converted_vl', readonly=True, store=True)
    total_fob_vl = fields.Float(related='import_declaration_id.total_fob_vl', readonly=True, store=True)
    insurance_converted_vl = fields.Float(related='import_declaration_id.insurance_converted_vl', readonly=True, store=True)
    afrmm_converted_vl = fields.Float(related='import_declaration_id.afrmm_converted_vl', readonly=True, store=True)
    total_cif = fields.Float(related='import_declaration_id.total_cif', readonly=True, store=True)
    siscomex_converted_vl = fields.Float(related='import_declaration_id.siscomex_converted_vl', readonly=True, store=True)
    
    name = fields.Char('Adição', size=3, required=True)
    sequence_addition = fields.Char('Sequencia', size=3, required=True)
    product_id = fields.Many2one('product.product', string='Produto', ondelete='restrict', index=True)
    manufacturer_code = fields.Char('Código Fabricante', size=60, required=True)
    manufacturer_description = fields.Char('Descrição Fabricante')
    uom_id = fields.Many2one('product.uom', string='UM', ondelete='set null', index=True)
    quantity = fields.Float(string='Qtde.', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1)
    amount_discount = fields.Float(string='Desconto', digits=dp.get_precision('Account'), default=0.00)
    price_unit = fields.Float(string='Preço Un', required=True, digits=dp.get_precision('Product Price'), default=0.00)
    weight_unit = fields.Float(string='Peso Un Liq (kg)', required=True, digits=(12,4), default=0.00)

    # impostos
    # II
    tax_ii_id = fields.Many2one('account.tax', string="Alíquota II", domain=[('domain', '=', 'ii')])
    ii_base_calculo = fields.Float('Base II', compute='_compute_ii', digits=dp.get_precision('Account'), default=0.00, store=True)
    ii_aliquota = fields.Float('II %', compute='_compute_ii', digits=(12,4), default=0.00)
    ii_valor = fields.Float('Valor II', digits=dp.get_precision('Account'),default=0.00, compute='_compute_ii', store=True)
    

    # Fileds Calculados
    amount_value = fields.Float(string='Valor FOB', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    amount_value_cl = fields.Float(string='Valor FOB', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    price_unit_cl = fields.Float(string='Preço Un', compute='_compute_item', digits=(12,5), readonly=True, store=True)
    amount_weight = fields.Float(string='Peso Liq (kg)', compute='_compute_item', digits=(12,4), readonly=True, store=True)
    freight_part = fields.Float(string='% Frete', compute='_compute_item', digits=(12,4), readonly=True, store=True)
    freight_value = fields.Float(string='Frete', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    insurance_part = fields.Float(string='% Seguro', compute='_compute_item', digits=(12,4), readonly=True, store=True)
    insurance_value = fields.Float(string='Seguro', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    afrmm_value = fields.Float(string='AFRMM', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    cif_value = fields.Float(string='Valor CIF', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    cif_afrmm_value = fields.Float(string='Valor CIF+AFRMM', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    siscomex_part = fields.Float(string='% SISCOMEX', compute='_compute_item', digits=(12,4), readonly=True, store=True)
    siscomex_value = fields.Float(string='SISCOMEX', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    
    
    
    drawback_number = fields.Char('Número Drawback', size=11)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if bool(self.product_id):
            self.manufacturer_description = self.product_id.name
            self.weight_unit = self.product_id.weight
            self.uom_id = self.product_id.uom_id
