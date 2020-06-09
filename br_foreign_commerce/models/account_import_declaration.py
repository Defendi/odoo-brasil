from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

DI_STATE = [('draft','Aberta'),('done','Pronta')]
DI_STATES= {'draft': [('readonly', False)]}

class ImportDeclaration(models.Model):
    _inherit = 'br_account.import.declaration'

    @api.depends('line_ids','freight_int_value','siscomex_value')
    def _compute_di(self):
        for di in self:
            total_fob_vl = sum(line.amount_value for line in di.line_ids)
            total_fob_lc = sum(line.amount_value_cl for line in di.line_ids)
            total_weight = sum((line.weight_unit * line.quantity) for line in di.line_ids)
            total_cif = sum(line.cif_value for line in di.line_ids)
            total_cif_afrmm = sum(line.cif_afrmm_value for line in di.line_ids)

            total_bc_ii = sum(line.ii_base_calculo for line in di.line_ids)
            total_ii = sum(line.ii_valor for line in di.line_ids)

            total_bc_ipi = sum(line.ipi_base_calculo for line in di.line_ids)
            total_ipi = sum(line.ipi_valor for line in di.line_ids)

            total_bc_pis = sum(line.pis_base_calculo for line in di.line_ids)
            total_pis = sum(line.pis_valor for line in di.line_ids)

            total_bc_cofins = sum(line.cofins_base_calculo for line in di.line_ids)
            total_cofins = sum(line.cofins_valor for line in di.line_ids)

            total_bc_icms = sum(line.icms_base_calculo for line in di.line_ids)
            total_icms = sum(line.icms_valor for line in di.line_ids)

            total_bc_icms_st = sum(line.icms_st_base_calculo for line in di.line_ids)
            total_icms_st = sum(line.icms_st_valor for line in di.line_ids)

            total_imposto = total_ii + total_ipi + total_icms + total_icms_st
            total_depesa = total_pis + total_cofins + di.siscomex_value
            total_nota = total_cif_afrmm + total_imposto + total_depesa

            vals = {
                'total_weight': total_weight,
                'total_fob_vl': total_fob_vl,
                'total_fob_lc': total_fob_lc,
                'total_cif': total_cif,
                'total_cif_afrmm': total_cif_afrmm,
                'total_produtos': total_cif_afrmm,
                'total_bc_ii': total_bc_ii,
                'total_ii': total_ii,
                'total_bc_ipi': total_bc_ipi,
                'total_ipi': total_ipi,
                'total_bc_pis': total_bc_pis,
                'total_pis': total_pis,
                'total_bc_cofins': total_bc_cofins,
                'total_cofins': total_cofins,
                'total_bc_icms': total_bc_icms,
                'total_icms': total_icms,
                'total_bc_icms_st': total_bc_icms_st,
                'total_icms_st': total_icms_st,
                'total_imposto': total_imposto,
                'total_depesa': total_depesa,
                'total_nota': total_nota,
                'espelho_bc_icms': total_bc_icms,
                'espelho_vl_icms': total_icms,
                'espelho_vl_icms_st': total_icms_st,
                'espelho_vl_ii': total_ii,
                'espelho_vl_ipi': total_ipi,
                'espelho_vl_other': total_depesa,
                'espelho_produtos': total_cif_afrmm,
                'espelho_frete': di.freight_int_value,
                'espelho_total_nfe': total_nota,
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

    state = fields.Selection(DI_STATE, string='Situação', default='draft')

    partner_id = fields.Many2one('res.partner', string='Exportador', readonly=True, states=DI_STATES)
    freight_value = fields.Float('Valor Frete', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    insurance_value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    tax_cambial = fields.Float('Tx. Cambial', digits=(12,6), default=0.00, readonly=True, states=DI_STATES)
    
    invoice_id = fields.Many2one('account.invoice', 'Fatura', ondelete='cascade', index=True, readonly=True, states=DI_STATES)
    name = fields.Char('Número da DI', size=10, required=True, readonly=True, states=DI_STATES)
    date_registration = fields.Date('Data de Registro', required=True, readonly=True, states=DI_STATES)
    state_id = fields.Many2one('res.country.state', 'Estado',domain="[('country_id.code', '=', 'BR')]", required=True, readonly=True, states=DI_STATES)
    location = fields.Char('Local', required=True, size=60, readonly=True, states=DI_STATES)
    date_release = fields.Date('Data de Liberação', required=True, readonly=True, states=DI_STATES)
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
    ], 'Transporte Internacional', required=True, default="1", readonly=True, states=DI_STATES)
    type_import = fields.Selection([
        ('1', '1 - Importação por conta própria'),
        ('2', '2 - Importação por conta e ordem'),
        ('3', '3 - Importação por encomenda'),
    ], 'Tipo de Importação', default='1', required=True, readonly=True, states=DI_STATES)
    thirdparty_cnpj = fields.Char('CNPJ', size=18, readonly=True, states=DI_STATES)
    thirdparty_state_id = fields.Many2one('res.country.state', 'Estado',domain="[('country_id.code', '=', 'BR')]", readonly=True, states=DI_STATES)
    exporting_code = fields.Char('Código do Exportador', required=True, size=60, readonly=True, states=DI_STATES)
    additional_information = fields.Text('Informações Adicionais', readonly=True, states=DI_STATES)

    company_id = fields.Many2one('res.company', 'Empresa', default=lambda self: self.env.user.company_id.id)#, readonly=True, states=DI_STATES)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Moeda Empresa", readonly=True)
    currency_purchase_id = fields.Many2one('res.currency', string="Moeda Compra", required=True, default=lambda self: self.env.user.company_id.currency_id.id)#, readonly=True, states=DI_STATES)

    afrmm_value = fields.Float('Valor AFRMM', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    siscomex_value = fields.Float('Valor SISCOMEX', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    freight_value = fields.Float('Valor Frete', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    freight_int_value = fields.Float('Valor Frete Interno', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    insurance_value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    tax_cambial = fields.Float('Taxa Cambial', digits=(12,6), default=0.00, readonly=True, states=DI_STATES)
    
    line_ids = fields.One2many('br_account.import.declaration.line','import_declaration_id', 'Linhas da DI', readonly=True, states=DI_STATES)

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
    total_produtos = fields.Float(string='Total Produtos', compute='_compute_di', digits=dp.get_precision('Account'))

    total_imposto = fields.Float(string='Total Imposto', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_depesa = fields.Float(string='Total Despesa', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_nota = fields.Float(string='Total nota', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)

    total_bc_ii = fields.Float(string='Total BC II', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_ii = fields.Float(string='Total II', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_bc_ipi = fields.Float(string='Total BC IPI', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_ipi = fields.Float(string='Total IPI', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_bc_pis = fields.Float(string='Total BC PIS', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_pis = fields.Float(string='Total PIS', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_bc_cofins = fields.Float(string='Total BC COFINS', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_cofins = fields.Float(string='Total COFINS', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_bc_icms = fields.Float(string='Total BC ICMS', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_icms = fields.Float(string='Total ICMS', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_bc_icms_st = fields.Float(string='Total BC ICMS ST', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_icms_st = fields.Float(string='Total ICMS ST', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)

    # Espelhos da NFe
    espelho_bc_icms = fields.Float(string='BC ICMS', compute='_compute_di', digits=dp.get_precision('Account'))
    espelho_vl_icms = fields.Float(string='Valor ICMS', compute='_compute_di', digits=dp.get_precision('Account'))
    espelho_vl_icms_st = fields.Float(string='Valor ICMS ST', compute='_compute_di', digits=dp.get_precision('Account'))
    espelho_vl_ii = fields.Float(string='Valor II', compute='_compute_di', digits=dp.get_precision('Account'))
    espelho_vl_ipi = fields.Float(string='Valor IPI', compute='_compute_di', digits=dp.get_precision('Account'))
    espelho_vl_other = fields.Float(string='Outras Despesas', compute='_compute_di', digits=dp.get_precision('Account'))
    espelho_produtos = fields.Float(string='Valor Produtos', compute='_compute_di', digits=dp.get_precision('Account'))
    espelho_frete = fields.Float(string='Valor Frete', compute='_compute_di', digits=dp.get_precision('Account'))
    espelho_total_nfe = fields.Float(string='Total NFe', compute='_compute_di', digits=dp.get_precision('Account'))
    
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
            price_unit_edoc = cif_afrmm_value / line.quantity 
            
            siscomex_part = (cif_value / line.total_cif) * 100 if line.total_cif > 0.0 else 0.0
            siscomex_value = line.siscomex_converted_vl * (siscomex_part / 100)
            
            vals = {
                'amount_value': amount, 
                'amount_value_cl': amount_local,
                'price_unit_cl': price_unit_local,
                'price_unit_edoc': price_unit_edoc,
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

    @api.depends('cif_afrmm_value','tax_ii_id','tax_ipi_id','ipi_inclui_ii_base','tax_pis_id','tax_cofins_id','tax_icms_id','tax_icms_st_id')
    def _compute_impostos(self):
        for line in self:
            ii_aliquota = 0.0
            ii_valor = 0.0
            ipi_aliquota = 0.0
            ipi_valor = 0.0
            pis_aliquota = 0.0
            pis_valor = 0.0
            cofins_aliquota = 0.0
            cofins_valor = 0.0
            icms_aliquota = 0.0
            icms_valor = 0.0
            icms_st_aliquota = 0.0
            icms_st_valor = 0.0
            ii_base_calculo = line.cif_afrmm_value
            ipi_base_calculo = line.cif_afrmm_value
            pis_base_calculo = line.cif_afrmm_value
            cofins_base_calculo = line.cif_afrmm_value
            icms_base_calculo = line.cif_afrmm_value + line.siscomex_value
            icms_st_base_calculo = 0.0

            if len(line.tax_ii_id) > 0:
                ii_aliquota += line.tax_ii_id.amount
                ii_valor += ii_base_calculo * (ii_aliquota/100)
                icms_base_calculo += ii_valor

            if bool(line.ipi_inclui_ii_base):
                ipi_base_calculo += ii_valor
            if len(line.tax_ipi_id) > 0:
                ipi_aliquota += line.tax_ipi_id.amount
                ipi_valor += ipi_base_calculo * (ipi_aliquota/100)
                icms_base_calculo += ipi_valor

            if len(line.tax_pis_id) > 0:
                pis_aliquota += line.tax_pis_id.amount
                pis_valor += pis_base_calculo * (pis_aliquota/100)
                icms_base_calculo += pis_valor

            if len(line.tax_cofins_id) > 0:
                cofins_aliquota += line.tax_cofins_id.amount
                cofins_valor += cofins_base_calculo * (cofins_aliquota/100)
                icms_base_calculo += cofins_valor

            if len(line.tax_icms_id) > 0:
                icms_aliquota += line.tax_icms_id.amount
                icms_base_calculo = icms_base_calculo / (1-(icms_aliquota/100))
                icms_valor += icms_base_calculo * (icms_aliquota/100)

            if len(line.tax_icms_st_id) > 0:
                icms_st_aliquota += line.tax_icms_st_id.amount
                icms_st_base_calculo = icms_base_calculo + (icms_base_calculo * (icms_st_aliquota/100))
                icms_st_valor += (icms_st_base_calculo * (icms_aliquota/100)) - icms_valor

            line.update({
                'ii_base_calculo': ii_base_calculo,
                'ii_aliquota': ii_aliquota,
                'ii_valor': ii_valor,
                'ipi_base_calculo': ipi_base_calculo,
                'ipi_aliquota': ipi_aliquota,
                'ipi_valor': ipi_valor,
                'pis_base_calculo': pis_base_calculo,
                'pis_aliquota': pis_aliquota,
                'pis_valor': pis_valor,
                'cofins_base_calculo': cofins_base_calculo,
                'cofins_aliquota': cofins_aliquota,
                'cofins_valor': cofins_valor,
                'icms_base_calculo': icms_base_calculo,
                'icms_aliquota': icms_aliquota,
                'icms_valor': icms_valor,
                'icms_st_base_calculo': icms_st_base_calculo,
                'icms_st_aliquota': icms_st_aliquota,
                'icms_st_valor': icms_st_valor,
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
    ii_base_calculo = fields.Float('Base II', compute='_compute_impostos', digits=dp.get_precision('Account'), default=0.00, store=True)
    ii_aliquota = fields.Float('II %', compute='_compute_impostos', digits=(12,4), default=0.00)
    ii_valor = fields.Float('Valor II', digits=dp.get_precision('Account'),default=0.00, compute='_compute_impostos', store=True)
    
    # IPI
    tax_ipi_id = fields.Many2one('account.tax', string="Alíquota IPI", domain=[('domain', '=', 'ipi')])
    ipi_inclui_ii_base = fields.Boolean('Inclui II na base',default=True)
    ipi_base_calculo = fields.Float('Base IPI', compute='_compute_impostos', digits=dp.get_precision('Account'), default=0.00, store=True)
    ipi_aliquota = fields.Float('IPI %', compute='_compute_impostos', digits=(12,4), default=0.00)
    ipi_valor = fields.Float('Valor IPI', digits=dp.get_precision('Account'),default=0.00, compute='_compute_impostos', store=True)

    # PIS
    tax_pis_id = fields.Many2one('account.tax', string="Alíquota PIS", domain=[('domain', '=', 'pis')])
    pis_base_calculo = fields.Float('Base PIS', compute='_compute_impostos', digits=dp.get_precision('Account'), default=0.00, store=True)
    pis_aliquota = fields.Float('PIS %', compute='_compute_impostos', digits=(12,4), default=0.00)
    pis_valor = fields.Float('Valor PIS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_impostos', store=True)

    # COFINS
    tax_cofins_id = fields.Many2one('account.tax', string="Alíquota COFINS", domain=[('domain', '=', 'cofins')])
    cofins_base_calculo = fields.Float('Base COFINS', compute='_compute_impostos', digits=dp.get_precision('Account'), default=0.00, store=True)
    cofins_aliquota = fields.Float('COFINS %', compute='_compute_impostos', digits=(12,4), default=0.00)
    cofins_valor = fields.Float('Valor COFINS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_impostos', store=True)

    # ICMS
    tax_icms_id = fields.Many2one('account.tax', string="Alíquota ICMS", domain=[('domain', '=', 'icms')])
    icms_base_calculo = fields.Float('Base ICMS', compute='_compute_impostos', digits=dp.get_precision('Account'), default=0.00, store=True)
    icms_aliquota = fields.Float('ICMS %', compute='_compute_impostos', digits=(12,4), default=0.00)
    icms_valor = fields.Float('Valor ICMS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_impostos', store=True)

    # ICMS ST
    tax_icms_st_id = fields.Many2one('account.tax', string="Alíquota ICMS ST", domain=[('domain', '=', 'icmsst')])
    icms_st_base_calculo = fields.Float('Base ICMS ST', compute='_compute_impostos', digits=dp.get_precision('Account'), default=0.00, store=True)
    icms_st_aliquota = fields.Float('ICMS ST %', compute='_compute_impostos', digits=(12,4), default=0.00)
    icms_st_valor = fields.Float('Valor ICMS ST', digits=dp.get_precision('Account'),default=0.00, compute='_compute_impostos', store=True)

    # Fileds Calculados
    amount_value = fields.Float(string='Valor FOB', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    amount_value_cl = fields.Float(string='Valor FOB', compute='_compute_item', digits=dp.get_precision('Account'), readonly=True, store=True)
    price_unit_cl = fields.Float(string='Preço Un', compute='_compute_item', digits=(12,5), readonly=True, store=True)
    price_unit_edoc = fields.Float(string='Preço Un eDoc', compute='_compute_item', digits=(12,5), readonly=True, store=True)
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
