from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

DI_STATE = [('draft','Aberta'),('to_invoice','Faturar'),('done','Finalizada')]
DI_STATES= {'draft': [('readonly', False)]}

class ImportDeclaration(models.Model):
    _inherit = 'br_account.import.declaration'

    @api.multi
    def confirm(self):
        for di in self:
            di.state = 'to_invoice'
 
    @api.multi
    def recalculate(self):
        self.ensure_one()
        vals = self._calcule_di()
        self.update(vals)

    def _calc_ratio(self, qty, total):
        if float_compare(qty,total,precision_rounding=4) == 0:
            return 1.0
        elif total > 0.0:
            return qty / total
        else:
            return 0

    def _calcule_di(self):
        freight_converted_vl = self.freight_value * self.tax_cambial
        insurance_converted_vl = self.insurance_value * self.tax_cambial
        total_desembaraco_vl = (freight_converted_vl + insurance_converted_vl + self.afrmm_value + self.siscomex_value)
        total_fob_vl = sum(line.amount_value for line in self.line_ids)
        total_fob_lc = sum(line.amount_value_cl for line in self.line_ids)
        total_weight = sum((line.weight_unit * line.quantity) for line in self.line_ids)
        smPrWeight = 0.0
        smPrValue = 0.0
        total_cif = 0.0
        total_bc_ii = 0.0
        total_ii = 0.0
        total_bc_ipi = 0.0
        total_ipi = 0.0
        total_bc_pis = 0.0
        total_pis = 0.0
        total_bc_cofins = 0.0
        total_cofins = 0.0
        total_bc_icms = 0.0
        total_icms = 0.0
        total_bc_icms_st = 0.0
        total_icms_st = 0.0
        tItens = len(self.line_ids)
        inlines = []
        for contador, line in enumerate(self.line_ids):
            if contador+1 < tItens:
                weight_part = self._calc_ratio((line.quantity * line.weight_unit), total_weight) * 100
                value_part = self._calc_ratio(line.amount_value_cl, total_fob_lc) * 100
            else:
                weight_part = 100 - smPrWeight
                value_part = 100 - smPrValue
            val_line = line._calcule_line(weight_part, value_part, freight_converted_vl, insurance_converted_vl, self.afrmm_value, self.siscomex_value)
            inlines += [(1,line.id,val_line)]
            smPrWeight += weight_part
            smPrValue += value_part
            total_cif += val_line['cif_value']
            total_bc_ii += val_line['ii_base_calculo'] 
            total_ii += val_line['ii_valor'] 
            total_bc_ipi += val_line['ipi_base_calculo'] 
            total_ipi += val_line['ipi_valor'] 
            total_bc_pis += val_line['pis_base_calculo']
            total_pis += val_line['pis_valor']
            total_bc_cofins += val_line['cofins_base_calculo']
            total_cofins += val_line['cofins_valor']
            total_bc_icms += val_line['icms_base_calculo']
            total_icms += val_line['icms_valor']
            total_bc_icms_st += val_line['icms_st_base_calculo']
            total_icms_st += val_line['icms_st_valor']

        total_cif_afrmm = total_cif + self.afrmm_value
        total_imposto = total_ii + total_ipi + total_icms + total_icms_st
        total_depesa = total_pis + total_cofins + self.siscomex_value
        total_nota = total_cif_afrmm + total_imposto + total_depesa

        vals = {
            'total_desembaraco_vl': total_desembaraco_vl,
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
            'espelho_frete': self.freight_int_value,
            'espelho_total_nfe': total_nota,
            'line_ids': inlines,
        }
        return vals

#     @api.depends('line_ids.amount_weight')
#     def _get_total_weight(self):
#         for record in self:
#             weight = 0.0
#             for line in record.line_ids:
#                 weight += line.amount_weight
#             record.total_weight = weight
# 
#     @api.onchange('total_weight')
#     def _set_total_weight(self):
#         for DI in self:
#             DI.freight_converted_vl = DI.freight_value * DI.tax_cambial
#             smPercent = 0.0
#             smFreight = 0.0
#             tItens = len(DI.line_ids)
#             for contador, line in enumerate(DI.line_ids):
#                 line.freight_total = DI.freight_value * DI.tax_cambial
#                 vlWeightBruto = line.quantity * line.weight_unit
#                 percentual = self._calc_ratio(vlWeightBruto, DI.total_weight) * 100
#                 if contador+1 < tItens:
#                     line.freight_part = percentual
#                     freight_value = DI.freight_converted_vl * (percentual / 100)
#                     line.freight_value = freight_value
#                 else:
#                     line.freight_part = 100 - smPercent
#                     line.freight_value = vlWeightBruto - smFreight
#                 smPercent += percentual
#                 smFreight += freight_value

    @api.depends('line_ids','freight_int_value','siscomex_value')
    def _compute_di(self):
        for DI in self:
            vals = DI._calcule_di()
            vals.pop('line_ids')
            DI.update(vals)

#     def _compute_invoice(self):
#         for di in self:
#             inv_lines = self.env['account.invoice.line'].search([('import_declaration_ids','in',[di.id])])
#             inv_ids = []
#             for inv_line in inv_lines:
#                 if inv_line.invoice_id.id not in inv_ids:
#                     inv_ids.append(inv_line.invoice_id.id)
#             invoices = self.env['account.invoice'].browse(inv_ids)
#             di.invoice_ids = invoices
#             di.invoice_count = len(invoices)

    state = fields.Selection(DI_STATE, string='Situação', default='draft')
    active = fields.Boolean(default=True)

    partner_id = fields.Many2one('res.partner', string='Exportador', readonly=True, states=DI_STATES)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')#, readonly=True, states=DI_STATES)
    freight_value = fields.Float('Valor Frete', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    insurance_value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    tax_cambial = fields.Float('Tx. Cambial', digits=(12,6), default=0.00)#, readonly=True, states=DI_STATES)
    
    invoice_id = fields.Many2one('account.invoice', 'Fatura', ondelete='cascade', index=True, readonly=True, states=DI_STATES)
    invoice_ids = fields.Many2many('account.invoice', compute="_compute_invoice", string='Bills', store=False)
    invoice_count = fields.Integer(compute="_compute_invoice", string='# Faturas', copy=False, default=0, store=False)

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
    currency_purchase_id = fields.Many2one('res.currency', string="Moeda Compra", required=True, default=lambda self: self.env.user.company_id.currency_id.id, readonly=True, states=DI_STATES)

    afrmm_value = fields.Float('Valor AFRMM', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    siscomex_value = fields.Float('Valor SISCOMEX', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    freight_value = fields.Float('Valor Frete', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    freight_int_value = fields.Float('Valor Frete Interno', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    insurance_value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    tax_cambial = fields.Float('Taxa Cambial', digits=(12,6), default=0.00, readonly=True, states=DI_STATES)
    
    line_ids = fields.One2many('br_account.import.declaration.line','import_declaration_id', 'Linhas da DI', copy=True, readonly=True, states=DI_STATES)

    # Campos Calculados
    total_weight = fields.Float('Peso Liq.', compute='_compute_di', digits=(12,4), readonly=True, store=True)
    freight_converted_vl = fields.Float('Frete', compute='_compute_di', digits=(12,4), readonly=True, store=True)
    insurance_converted_vl = fields.Float('Seguro', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    afrmm_converted_vl = fields.Float('AFRMM', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    siscomex_converted_vl = fields.Float('SISCOMEX', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_desembaraco_vl = fields.Float('Total Desembaraço', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_fob_vl = fields.Float('Total FOB', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_fob_lc = fields.Float('Total FOB', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_cif = fields.Float(string='Total CIF', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_cif_afrmm = fields.Float(string='Total CIF+AFRMM', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_produtos = fields.Float(string='Total Produtos', compute='_compute_di', digits=dp.get_precision('Account'), store=True)

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
    espelho_bc_icms = fields.Float(string='BC ICMS', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    espelho_vl_icms = fields.Float(string='Valor ICMS', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    espelho_vl_icms_st = fields.Float(string='Valor ICMS ST', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    espelho_vl_ii = fields.Float(string='Valor II', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    espelho_vl_ipi = fields.Float(string='Valor IPI', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    espelho_vl_other = fields.Float(string='Outras Despesas', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    espelho_produtos = fields.Float(string='Valor Produtos', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    espelho_frete = fields.Float(string='Valor Frete', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    espelho_total_nfe = fields.Float(string='Total NFe', compute='_compute_di', digits=dp.get_precision('Account'), store=True)

#     @api.multi
#     def action_view_invoice(self):
# 
#         action = self.env.ref('account.action_invoice_tree2')
#         result = action.read()[0]
# 
#         #override the context to get rid of the default filtering
#         result['context'] = {'type': 'in_invoice', 'default_import_id': self.id}
# 
#         if not self.invoice_ids:
#             # Choose a default account journal in the same currency in case a new invoice is created
#             journal_domain = [
#                 ('type', '=', 'purchase'),
#                 ('company_id', '=', self.company_id.id),
#                 ('currency_id', '=', self.currency_id.id),
#             ]
#             default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
#             if default_journal_id:
#                 result['context']['default_journal_id'] = default_journal_id.id
#         else:
#             # Use the same account journal than a previous invoice
#             result['context']['default_journal_id'] = self.invoice_ids[0].journal_id.id
# 
#         #choose the view_mode accordingly
#         if len(self.invoice_ids) != 1:
#             result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
#         elif len(self.invoice_ids) == 1:
#             res = self.env.ref('account.invoice_supplier_form', False)
#             result['views'] = [(res and res.id or False, 'form')]
#             result['res_id'] = self.invoice_ids.id
#         return result
    
class ImportDeclarationLine(models.Model):
    _inherit = 'br_account.import.declaration.line'
    _order = 'import_declaration_id, name, sequence_addition, id'

    def _calcule_line(self, txFreight, txValue, vlFreight, vlInsurance, vlAfrmm, vlSiscomex):
        amount_value = (self.quantity * self.price_unit) - self.amount_discount
        amount_weight = self.weight_unit * self.quantity
        amount_value_cl = amount_value * self.tax_cambial
        price_unit_cl = amount_value_cl / self.quantity if self.quantity > 0.0 else 0.0
        
        freight_total = vlFreight
        freight_part = txFreight
        freight_value = vlFreight * (txFreight/100)
        insurance_total = vlInsurance
        insurance_part = txValue
        insurance_value = vlInsurance * (txValue/100)
        afrmm_total = vlAfrmm
        afrmm_part = txValue
        afrmm_value = vlAfrmm * (txValue/100)
        siscomex_total = vlSiscomex
        siscomex_part = txValue
        siscomex_value = vlSiscomex * (txValue/100)

        cif_value = amount_value_cl + freight_value + insurance_value
        cif_afrmm_value = cif_value + afrmm_value

        price_unit_edoc = cif_afrmm_value / self.quantity 

        ii_base_calculo = cif_afrmm_value
        ipi_base_calculo = cif_afrmm_value 
        pis_base_calculo = cif_afrmm_value
        cofins_base_calculo = cif_afrmm_value
        icms_base_calculo = cif_afrmm_value + siscomex_value

        ii_aliquota = self.tax_ii_id.amount if len(self.tax_ii_id) > 0 else 0.0
        ii_valor = ii_base_calculo * (ii_aliquota/100) if ii_aliquota != 0.0 else 0.0

        if self.ipi_inclui_ii_base:
            ipi_base_calculo += ii_valor
        ipi_aliquota = self.tax_ipi_id.amount if len(self.tax_ipi_id) > 0 else 0.0
        ipi_valor = ipi_base_calculo * (ipi_aliquota/100) if ipi_aliquota != 0.0 else 0.0

        pis_aliquota = self.tax_pis_id.amount if len(self.tax_pis_id) > 0 else 0.0
        pis_valor = pis_base_calculo * (pis_aliquota/100) if pis_aliquota != 0.0 else 0.0

        cofins_aliquota = self.tax_cofins_id.amount if len(self.tax_cofins_id) > 0 else 0.0
        cofins_valor = cofins_base_calculo * (cofins_aliquota/100) if cofins_aliquota != 0.0 else 0.0

        icms_base_calculo += (ii_valor + ipi_valor + pis_valor + cofins_valor)
        icms_aliquota = self.tax_icms_id.amount if len(self.tax_icms_id) > 0 else 0.0
        icms_base_calculo = icms_base_calculo / (1-(icms_aliquota/100)) if icms_aliquota != 0.0 else 0.0
        icms_valor = icms_base_calculo * (icms_aliquota/100) if icms_aliquota != 0.0 else 0.0

        icms_st_aliquota = self.tax_icms_st_id.amount if len(self.tax_icms_st_id) > 0 else 0.0
        icms_st_base_calculo = icms_base_calculo + (icms_base_calculo * (icms_st_aliquota/100)) if icms_st_aliquota != 0.0 else 0.0
        icms_st_valor = (icms_st_base_calculo * (icms_aliquota/100)) - icms_valor if icms_st_aliquota != 0.0 else 0.0

        vals = {
            'amount_value': amount_value, 
            'amount_weight': amount_weight,
            'amount_value_cl': amount_value_cl,
            'price_unit_cl': price_unit_cl,
            'freight_total': freight_total,
            'freight_part': freight_part,
            'freight_value': freight_value,
            'insurance_total': insurance_total,
            'insurance_part': insurance_part,
            'insurance_value': insurance_value,
            'afrmm_total': afrmm_total,
            'afrmm_part': afrmm_part,
            'afrmm_value': afrmm_value,
            'siscomex_total': siscomex_total,
            'siscomex_part': siscomex_part,
            'siscomex_value': siscomex_value,
            'cif_value': cif_value,
            'cif_afrmm_value': cif_afrmm_value,
            'price_unit_edoc': price_unit_edoc,
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
        }
        return vals

    @api.depends('quantity','price_unit','amount_discount','weight_unit','tax_ii_id','tax_ipi_id',
                 'ipi_inclui_ii_base','tax_pis_id','tax_cofins_id','tax_icms_id','tax_icms_st_id')
    def _compute_line(self):
#         for line in self:
#             vals = line._calcule_line(0.0,0.0,0.0,0.0,0.0,0.0)
#             line.update(vals)
        pass
    
    import_declaration_id = fields.Many2one('br_account.import.declaration', 'DI', ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='import_declaration_id.currency_id', readonly=True)
    currency_purchase_id = fields.Many2one('res.currency', related='import_declaration_id.currency_purchase_id', readonly=True)
    tax_cambial = fields.Float(related='import_declaration_id.tax_cambial', readonly=True, store=True)
    
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

    weight_part = fields.Float(string='% Peso Liq', digits=(12,4), readonly=True)
    value_part = fields.Float(string='% Valor FOB', digits=(12,4), readonly=True)

    # Fileds Calculados
    amount_value = fields.Float(string='Valor FOB', compute='_compute_line', digits=(12,3), readonly=True, store=True)
    amount_value_cl = fields.Float(string='Valor FOB', compute='_compute_line', digits=(12,3), readonly=True, store=True)
    price_unit_cl = fields.Float(string='Preço Un', compute='_compute_line', digits=(12,5), readonly=True, store=True)
    amount_weight = fields.Float(string='Peso Liq (kg)', compute='_compute_line', digits=(12,4), readonly=True, store=True)

    freight_total = fields.Float(string='Frete Total', compute='_compute_line', digits=(12,4), readonly=True, store=True)
    freight_part = fields.Float(string='Frete Total', compute='_compute_line', digits=(12,6), readonly=True, store=True)
    freight_value = fields.Float(string='Frete Valor', compute='_compute_line', digits=(12,4), readonly=True, store=True)
    
    insurance_total = fields.Float(string='Seguro Total', compute='_compute_line', digits=(12,4), readonly=True, store=True)
    insurance_part = fields.Float(string='Seguro %', compute='_compute_line', digits=(12,6), readonly=True, store=True)
    insurance_value = fields.Float(string='Seguro Valor', compute='_compute_line', digits=(12,3), readonly=True, store=True)

    afrmm_total = fields.Float(string='AFRMM Total', compute='_compute_line', digits=(12,4), readonly=True, store=True)
    afrmm_part = fields.Float(string='AFRMM %', compute='_compute_line', digits=(12,6), readonly=True, store=True)
    afrmm_value = fields.Float(string='AFRMM Valor', compute='_compute_line', digits=(12,3), readonly=True, store=True)

    siscomex_total = fields.Float(string='SISCOMEX Total', compute='_compute_line', digits=(12,4), readonly=True, store=True)
    siscomex_part = fields.Float(string='SISCOMEX %', compute='_compute_line', digits=(12,6), readonly=True, store=True)
    siscomex_value = fields.Float(string='SISCOMEX Valor', compute='_compute_line', digits=(12,3), readonly=True, store=True)

    cif_value = fields.Float(string='Valor CIF', compute='_compute_line', digits=(12,3), readonly=True, store=True)
    cif_afrmm_value = fields.Float(string='Valor CIF+AFRMM', compute='_compute_line', digits=(12,3), readonly=True, store=True)

    outras_depesas = fields.Float(string='Outras Despesas', compute='_compute_line', digits=(12,3), readonly=True, store=True)
    price_unit_edoc = fields.Float(string='Preço Un eDoc', compute='_compute_line', digits=(12,5), readonly=True, store=True)

    # impostos
    # II
    tax_ii_id = fields.Many2one('account.tax', string="Alíquota II", domain=[('domain', '=', 'ii'),('type_tax_use','=','purchase')])
    ii_base_calculo = fields.Float('Base II', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00)
    ii_aliquota = fields.Float('II %', compute='_compute_line', digits=(12,4), default=0.00)
    ii_valor = fields.Float('Valor II', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line')
    
    # IPI
    tax_ipi_id = fields.Many2one('account.tax', string="Alíquota IPI", domain=[('domain', '=', 'ipi'),('type_tax_use','=','purchase')])
    ipi_inclui_ii_base = fields.Boolean('Inclui II na base',default=True)
    ipi_base_calculo = fields.Float('Base IPI', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00)
    ipi_aliquota = fields.Float('IPI %', compute='_compute_line', digits=(12,4), default=0.00)
    ipi_valor = fields.Float('Valor IPI', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line')

    # PIS
    tax_pis_id = fields.Many2one('account.tax', string="Alíquota PIS", domain=[('domain', '=', 'pis'),('type_tax_use','=','purchase')])
    pis_base_calculo = fields.Float('Base PIS', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00)
    pis_aliquota = fields.Float('PIS %', compute='_compute_line', digits=(12,4), default=0.00)
    pis_valor = fields.Float('Valor PIS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line')

    # COFINS
    tax_cofins_id = fields.Many2one('account.tax', string="Alíquota COFINS", domain=[('domain', '=', 'cofins'),('type_tax_use','=','purchase')])
    cofins_base_calculo = fields.Float('Base COFINS', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00)
    cofins_aliquota = fields.Float('COFINS %', compute='_compute_line', digits=(12,4), default=0.00)
    cofins_valor = fields.Float('Valor COFINS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line')

    # ICMS
    tax_icms_id = fields.Many2one('account.tax', string="Alíquota ICMS", domain=[('domain', '=', 'icms'),('type_tax_use','=','purchase')])
    icms_base_calculo = fields.Float('Base ICMS', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00)
    icms_aliquota = fields.Float('ICMS %', compute='_compute_line', digits=(12,4), default=0.00)
    icms_valor = fields.Float('Valor ICMS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line')

    # ICMS ST
    tax_icms_st_id = fields.Many2one('account.tax', string="Alíquota ICMS ST", domain=[('domain', '=', 'icmsst'),('type_tax_use','=','purchase')])
    icms_st_base_calculo = fields.Float('Base ICMS ST', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00)
    icms_st_aliquota = fields.Float('ICMS ST %', compute='_compute_line', digits=(12,4), default=0.00)
    icms_st_valor = fields.Float('Valor ICMS ST', compute='_compute_line', digits=dp.get_precision('Account'),default=0.00)

    drawback_number = fields.Char('Número Drawback', size=11)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if bool(self.product_id):
            self.manufacturer_description = self.product_id.name
            self.weight_unit = self.product_id.weight
            self.uom_id = self.product_id.uom_id

#     @api.onchange('weight_unit')
#     def _set_weight_unit(self):
#         res = self.import_declaration_id._sum_weight(self)
#         self.freight_part = self.import_declaration_id._calc_ratio(self.amount_weight,res)*100

