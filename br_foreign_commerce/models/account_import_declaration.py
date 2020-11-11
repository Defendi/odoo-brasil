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
    def reopen(self):
        for di in self:
            di.state = 'draft'
 
    @api.multi
    def recalculate(self):
        self.ensure_one()
        vals = self._calcule_di()
        self.update(vals)

    def _calc_ratio(self, qty, total):
        if float_compare(qty,total,precision_rounding=4) == 0:
            return 1.0
        elif total > 0.0 and qty > 0.0:
            return qty / total
        else:
            return 0

    def _calc_ratio_di(self):
        self.ensure_one()
        total_weight = sum((line.weight_unit * line.quantity) for line in self.line_ids)
        total_volume = sum((line.volume_unit * line.quantity) for line in self.line_ids)
        total_qty = sum(line.quantity for line in self.line_ids)
        total_prod = sum(((line.quantity * line.price_vucv) - line.amount_discount) * self.tax_cambial for line in self.line_ids)
        total_aduaneiro = (((self.freight_value + self.insurance_value) * self.tax_cambial) +  self.customs_value)
        ratio = total_aduaneiro / total_qty

        tItens = len(self.line_ids)
        smPrWeight = 0.0
        smPrValue = 0.0
        smQuantity = 0.0
        smVolume = 0.0
        inlines = {}

        for contador, line in enumerate(self.line_ids):
            if contador+1 < tItens:
                value_prod = ((line.quantity * line.price_vucv) - line.amount_discount) * self.tax_cambial
                weight_part = self._calc_ratio((line.quantity * line.weight_unit), total_weight) * 100 if line.weight_unit > 0.0 else 0.0
                volume_part = self._calc_ratio((line.quantity * line.volume_unit), total_volume) * 100 if line.weight_unit > 0.0 else 0.0
                value_part = self._calc_ratio(value_prod, total_prod) * 100 if value_prod > 0.0 else 0.0
                quant_part = ((ratio * line.quantity) / total_aduaneiro) * 100 #self._calc_ratio(line.quantity, total_qty) * 100 if line.quantity > 0.0 else 0.0
            else:
                weight_part = 100.0 - smPrWeight
                volume_part = 100.0 - smVolume 
                value_part = 100.0 - smPrValue
                quant_part = ratio #100.0 - smQuantity 
                
            if bool(inlines.get(line.name,False)):
                inlines[line.name][line.sequence_addition] = (line.id,weight_part,value_part,volume_part,quant_part)
            else:
                inlines[line.name] = {line.sequence_addition: (line.id,weight_part,value_part,volume_part,quant_part)}
            smPrWeight += weight_part
            smPrValue += value_part
            smQuantity += quant_part
            smVolume += volume_part
        return inlines

    def _calcule_di(self):
        freight_converted_vl = self.freight_value * self.tax_cambial
        insurance_converted_vl = self.insurance_value * self.tax_cambial
        total_desembaraco_vl = (freight_converted_vl + insurance_converted_vl + self.afrmm_value + self.siscomex_value + self.customs_value)
        total_fob_vl = sum(line.amount_vucv for line in self.line_ids)
        total_fob_lc = sum(line.amount_value_cl for line in self.line_ids)
        total_weight = sum((line.weight_unit * line.quantity) for line in self.line_ids)
        total_volume = sum((line.volume_unit * line.quantity) for line in self.line_ids)
        total_produto_qty = sum(line.quantity for line in self.line_ids)
        smPrWeight = 0.0
        smPrValue = 0.0
        smQuantity = 0.0
        smVolume = 0.0
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
        total_produtos = 0.0
        total_aduaneiro = (((self.freight_value + self.insurance_value) * self.tax_cambial) +  self.customs_value)
        tItens = len(self.line_ids)
        ratio = total_aduaneiro / total_produto_qty
        for contador, line in enumerate(self.line_ids):
            if contador+1 < tItens:
                #value_prod = ((line.quantity * line.price_vucv) - line.amount_discount) * self.tax_cambial
                weight_part = self._calc_ratio((line.quantity * line.weight_unit), total_weight) * 100 if line.weight_unit > 0.0 else 0.0
                value_part = self._calc_ratio(line.amount_value_cl, total_fob_lc) * 100 if line.amount_value_cl > 0.0 else 0.0
                volume_part = self._calc_ratio((line.quantity * line.volume_unit), total_volume) * 100 if line.volume_unit > 0.0 else 0.0
                quant_part = ((ratio * line.quantity) / total_aduaneiro) * 100 #self._calc_ratio(line.quantity, total_produto_qty) * 100 if line.quantity > 0.0 else 0.0
            else:
                weight_part = 100 - smPrWeight
                value_part = 100 - smPrValue
                volume_part = 100 - smVolume
                quant_part = 100 - smQuantity
            val_line = line._calcule_line(weight_part, value_part, quant_part, volume_part, freight_converted_vl, insurance_converted_vl, self.afrmm_value, self.siscomex_value, self.customs_value, self.other_value)
            smPrWeight += weight_part
            smPrValue += value_part
            smQuantity += quant_part
            smVolume += volume_part
            total_cif += val_line['cif_value']
            total_bc_ii += val_line['ii_base_calculo'] 
            total_ii += val_line['ii_valor'] 
            total_produtos += val_line['price_unit_edoc'] * line.quantity
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
            line.write(val_line)

        total_cif_afrmm = total_cif + self.afrmm_value
        total_imposto = total_ipi + total_icms + total_icms_st
        total_despesa = total_pis + total_cofins #+ self.siscomex_value + self.afrmm_value
        total_nota = total_produtos + total_imposto + total_despesa

        vals = {
            'total_produtos': total_produtos,
            'total_produto_qty': total_produto_qty,
            'total_weight': total_weight,
            'total_volume': total_volume,
            'total_desembaraco_vl': total_desembaraco_vl,
            'total_fob_vl': total_fob_vl,
            'total_fob_lc': total_fob_lc,
            'total_cif': total_cif,
            'total_cif_afrmm': total_cif_afrmm,
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
            'total_depesa': total_despesa,
            'total_nota': total_nota,
            'espelho_bc_icms': total_bc_icms,
            'espelho_vl_icms': total_icms,
            'espelho_vl_icms_st': total_icms_st,
            'espelho_vl_ii': total_ii,
            'espelho_vl_ipi': total_ipi,
            'espelho_vl_other': total_despesa,
            'espelho_produtos': total_produtos,
            'espelho_total_nfe': total_nota,
            #'line_ids': inlines,
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

    @api.depends('line_ids','other_value','siscomex_value','freight_mode', 'tax_cambial',
                 'customs_value', 'afrmm_value', 'freight_value', 'insurance_value')
    def _compute_di(self):
        for DI in self:
            vals = DI._calcule_di()
            DI.update(vals)

    def _compute_invoice(self):
        for di in self:
            inv_lines = self.env['account.invoice.line'].search([('import_declaration_ids','in',[di.id])])
            inv_ids = []
            for inv_line in inv_lines:
                if inv_line.invoice_id.id not in inv_ids:
                    inv_ids.append(inv_line.invoice_id.id)
            invoices = self.env['account.invoice'].browse(inv_ids)
            di.invoice_ids = invoices
            di.invoice_count = len(invoices)

    state = fields.Selection(DI_STATE, string='Situação', default='draft')
    active = fields.Boolean(default=True)

    partner_id = fields.Many2one('res.partner', string='Exportador', domain="[('supplier', '=', True)]", readonly=True, states=DI_STATES)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True, 
                                         domain=[('fiscal_type','in',('import','export'))], states=DI_STATES)
    freight_value = fields.Float('Valor Frete', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    insurance_value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    tax_cambial = fields.Float('Tx. Cambial', digits=(12,6), default=0.00)#, readonly=True, states=DI_STATES)
    
#     invoice_id = fields.Many2one('account.invoice', 'Fatura', ondelete='cascade', index=True, readonly=True, states=DI_STATES)
    invoice_ids = fields.Many2many('account.invoice', compute="_compute_invoice", string='Bills', store=False)
    invoice_count = fields.Integer(compute="_compute_invoice", string='# Faturas', copy=False, default=0, store=False)

    name = fields.Char('Número da DI', size=10, required=True, readonly=True, states=DI_STATES)
    date_registration = fields.Date('Data de Registro', readonly=True, states=DI_STATES)
    state_id = fields.Many2one('res.country.state', 'Estado',domain="[('country_id.code', '=', 'BR')]", readonly=True, states=DI_STATES)
    location = fields.Char('Local', size=60, readonly=True, states=DI_STATES)
    date_release = fields.Date('Data de Liberação', readonly=True, states=DI_STATES)
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
    ], 'Transporte Internacional', default="1", readonly=True, states=DI_STATES)
    type_import = fields.Selection([
        ('1', '1 - Importação por conta própria'),
        ('2', '2 - Importação por conta e ordem'),
        ('3', '3 - Importação por encomenda'),
    ], 'Tipo de Importação', default='1', readonly=True, states=DI_STATES)
    thirdparty_cnpj = fields.Char('CNPJ', size=18, readonly=True, states=DI_STATES)
    thirdparty_state_id = fields.Many2one('res.country.state', 'Estado',domain="[('country_id.code', '=', 'BR')]", readonly=True, states=DI_STATES)
    exporting_code = fields.Char('Código do Exportador', size=60, readonly=True, states=DI_STATES)
    additional_information = fields.Text('Informações Adicionais', readonly=True, states=DI_STATES)

    company_id = fields.Many2one('res.company', 'Empresa', default=lambda self: self.env.user.company_id.id)#, readonly=True, states=DI_STATES)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Moeda Empresa", readonly=True)
    currency_purchase_id = fields.Many2one('res.currency', string="Moeda Compra", required=True, default=lambda self: self.env.user.company_id.currency_id.id, readonly=True, states=DI_STATES)

    afrmm_value = fields.Float('Valor AFRMM', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    siscomex_value = fields.Float('Valor SISCOMEX', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    customs_value = fields.Float('THC + THC2', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES,help="Despesas com THC,THC2 e outras despesas de armazenagem em terminal.")
    freight_mode  = fields.Selection([('P', 'Peso'),('V', 'Volume'),('Q', 'Quantidade')], 'Mod.Calculo Frete', default='Q', required=True, readonly=True, states=DI_STATES) 
    freight_value = fields.Float('Valor Frete', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    other_value = fields.Float('Outras Taxas', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES, oldname="freight_int_value")
    insurance_value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
#     _value = fields.Float('Valor Seguro', digits=dp.get_precision('Account'), default=0.00, readonly=True, states=DI_STATES)
    
    line_ids = fields.One2many('br_account.import.declaration.line','import_declaration_id', 'Linhas da DI', copy=True, readonly=True, states=DI_STATES)

    # Campos Calculados
    total_produtos = fields.Float(string='Total Produtos', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    total_produto_qty = fields.Float(string='Total Qtde. Produto', compute='_compute_di', digits=dp.get_precision('Account'), store=True)
    total_weight = fields.Float('Peso Liq.', compute='_compute_di', digits=(12,4), readonly=True, store=True)
    total_volume = fields.Float('Volume', compute='_compute_di', digits=(18,6), readonly=True, store=True)
    
    
    freight_converted_vl = fields.Float('Frete', compute='_compute_di', digits=(12,4), readonly=True, store=True)
    insurance_converted_vl = fields.Float('Seguro', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    afrmm_converted_vl = fields.Float('AFRMM', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    siscomex_converted_vl = fields.Float('SISCOMEX', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_desembaraco_vl = fields.Float('Total Desembaraço', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_fob_vl = fields.Float('Total FOB', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_fob_lc = fields.Float('Total FOB', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_cif = fields.Float(string='Total CIF', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)
    total_cif_afrmm = fields.Float(string='Total CIF+AFRMM', compute='_compute_di', digits=dp.get_precision('Account'), readonly=True, store=True)

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

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if bool(self.partner_id):
            self.currency_purchase_id = self.partner_id.property_purchase_currency_id
    
    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id(self):
        fpos = self.fiscal_position_id or self.partner_id.property_purchase_fiscal_position_id
        if fpos:
            for line in self.line_ids:
                #                                 product,         partner,         fiscal_classification,                   service_type, issqn_tipo, analytic
                vals = fpos.map_tax_extra_values(line.product_id, self.partner_id, line.product_id.fiscal_classification_id, False,        False,      False)
                line.tax_ii_id = vals.get('tax_ii_id',False)
                line.tax_ipi_id = vals.get('tax_ipi_id',False)
                line.tax_pis_id = vals.get('tax_pis_id',False)
                line.tax_cofins_id = vals.get('tax_cofins_id',False)
                line.tax_icms_id = vals.get('tax_icms_id',False)
                line.icms_difer = True if vals.get('icms_aliquota_diferimento',0.0) > 0.0 else False
                line.icms_aliq_difer = vals.get('icms_aliquota_diferimento',0.0)
                line.tax_icms_st_id = vals.get('tax_icms_st_id',False)

    @api.onchange('currency_purchase_id','company_id','date_registration')
    def _onchange_currency_rate_date(self):
        if bool(self.currency_purchase_id) and bool(self.company_id) and bool(self.date_registration):
            rate = self.env['res.currency.rate'].search([('company_id','=',self.company_id.id),
                                                  ('currency_id','=',self.currency_purchase_id.id),
                                                  ('name','=',self.date_registration)])
            if bool(rate):
                self.tax_cambial = rate.rate

    @api.multi
    def action_view_invoice(self):
 
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]
 
        #override the context to get rid of the default filtering
        result['context'] = {'default_type': 'in_invoice', 
                             'default_import_id': self.id,
                             'default_fiscal_position_id': self.fiscal_position_id.id or self.partner_id.property_account_position_id.id,
                             'default_partner_id': self.partner_id.id,
                             }
 
        if not self.invoice_ids:
            # Choose a default account journal in the same currency in case a new invoice is created
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.currency_id.id),
            ]
            default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                result['context']['default_journal_id'] = default_journal_id.id
        else:
            # Use the same account journal than a previous invoice
            result['context']['default_journal_id'] = self.invoice_ids[0].journal_id.id
 
        #choose the view_mode accordingly
        if len(self.invoice_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        elif len(self.invoice_ids) == 1:
            res = self.env.ref('account.invoice_supplier_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.invoice_ids.id
        return result

class ImportDeclarationLine(models.Model):
    _inherit = 'br_account.import.declaration.line'
    _order = 'import_declaration_id, name, sequence_addition, id'

    def _calcule_line(self, txWheight, txValue, txQtde, txVolume, vlFreight, vlInsurance, vlAfrmm, vlSiscomex, vlDespAdn, vlOther):
        
        amount_vucv = (self.quantity * self.price_vucv) - self.amount_discount
        amount_weight = self.weight_unit * self.quantity
        amount_value_fob = amount_vucv * self.tax_cambial
        price_unit_fob = amount_value_fob / self.quantity if self.quantity > 0.0 else 0.0

        if self.import_declaration_id.freight_mode == 'P':
            txFreight = txWheight
        elif self.import_declaration_id.freight_mode == 'V':
            txFreight = txVolume
        else:
            txFreight = txQtde

        freight_total = vlFreight
        freight_part = txFreight
        freight_value = vlFreight * (txFreight/100)
        insurance_total = vlInsurance
        insurance_part = txValue
        insurance_value = vlInsurance * (txValue/100)
        afrmm_total = vlAfrmm
        afrmm_part = txQtde
        afrmm_value = vlAfrmm * (txQtde/100)
        siscomex_total = vlSiscomex
        siscomex_part = txQtde
        siscomex_value = vlSiscomex * (txQtde/100)
        desp_aduan_total = vlDespAdn
        desp_aduan_part = txFreight
        desp_aduan_value = vlDespAdn * (txFreight/100)
        other_taxs_total = vlOther
        other_taxs_part = txQtde
        other_taxs_value = vlOther * (txQtde/100)

        cif_value = amount_value_fob + freight_value + desp_aduan_value + insurance_value
        subtotal = (cif_value + siscomex_value + afrmm_value + other_taxs_value)

        ii_aliquota = self.tax_ii_id.amount if len(self.tax_ii_id) > 0 else 0.0
        if ii_aliquota > 0.0:
            ii_base_calculo = amount_value_fob + freight_value + insurance_value + desp_aduan_value
            ii_valor = ii_base_calculo * (ii_aliquota/100) if ii_aliquota != 0.0 else 0.0
#             if self.tax_ii_id.price_include:
            subtotal += ii_valor
        else:
            ii_base_calculo = 0.0
            ii_valor = 0.0

        price_cost = subtotal

        ipi_aliquota = self.tax_ipi_id.amount if len(self.tax_ipi_id) > 0 else 0.0
        if ipi_aliquota > 0.0:
            ipi_base_calculo = amount_value_fob + freight_value + insurance_value + desp_aduan_value
            if self.ipi_inclui_ii_base:
                ipi_base_calculo += ii_valor
            ipi_valor = ipi_base_calculo * (ipi_aliquota/100) if ipi_aliquota != 0.0 else 0.0
#             if self.tax_ipi_id.price_include:
            price_cost += ipi_valor
        else:
            ipi_base_calculo = 0.0
            ipi_valor = 0.0

        pis_aliquota = self.tax_pis_id.amount if len(self.tax_pis_id) > 0 else 0.0
        if pis_aliquota > 0.0:
            pis_base_calculo = amount_value_fob + freight_value + insurance_value + desp_aduan_value
            pis_valor = pis_base_calculo * (pis_aliquota/100) if pis_aliquota != 0.0 else 0.0
#             if self.tax_pis_id.price_include:
            price_cost += pis_valor
        else:
            pis_base_calculo = 0.0
            pis_valor = 0.0

        cofins_aliquota = self.tax_cofins_id.amount if len(self.tax_cofins_id) > 0 else 0.0
        if cofins_aliquota > 0.0:
            cofins_base_calculo = amount_value_fob + freight_value + insurance_value + desp_aduan_value
            cofins_valor = cofins_base_calculo * (cofins_aliquota/100) if cofins_aliquota != 0.0 else 0.0
#             if self.tax_cofins_id.price_include:
            price_cost += cofins_valor
        else:
            cofins_base_calculo = 0.0
            cofins_valor = 0.0

        
        icms_aliquota = self.tax_icms_id.amount if len(self.tax_icms_id) > 0 else 0.0
        if icms_aliquota > 0.0:
            if self.icms_fator_manual > 0.0:
                icms_fator = self.icms_fator_manual
            else:
                icms_fator = 100.0 - icms_aliquota
            icms_base_calculo = (cif_value + siscomex_value + afrmm_value + ii_valor + ipi_valor + pis_valor + cofins_valor) / (icms_fator/100) if (icms_fator/100) != 0.0 else 0.0
            icms_valor = icms_base_calculo * (icms_aliquota/100) if icms_aliquota != 0.0 else 0.0
            if self.icms_difer and self.icms_aliq_difer > 0.0:
                icms_valor = icms_valor * ((100-self.icms_aliq_difer)/100)
            
#             if self.tax_icms_id.price_include:
            price_cost += icms_valor
        else:
            icms_base_calculo = 0.0
            icms_fator = 0.0
            icms_valor = 0.0
            
        icms_st_aliquota = self.tax_icms_st_id.amount if len(self.tax_icms_st_id) > 0 else 0.0
        if icms_st_aliquota > 0.0:
            icms_st_base_calculo = icms_base_calculo + (icms_base_calculo * (icms_st_aliquota/100)) if icms_st_aliquota != 0.0 else 0.0
            icms_st_valor = (icms_st_base_calculo * (icms_aliquota/100)) - icms_valor if icms_st_aliquota != 0.0 else 0.0
            if self.tax_icms_st_id.price_include:
                price_cost += icms_st_valor
        else:
            icms_st_base_calculo = 0.0
            icms_st_valor = 0.0

#         price_cost = price_cost / self.quantity if self.quantity > 0.0 else 0.0

        #price_cost = cif_afrmm_value + siscomex_value

        if self.quantity > 0.0:
            price_unit_edoc = round(subtotal, 2) / self.quantity if self.quantity > 0.0 else 0.0
        else: 
            price_unit_edoc = 0.0
        
#         icms_base_calculo = cif_value + cif_afrmm_value + siscomex_value


        vals = {
            'weight_part': txFreight,
            'value_part': txValue,
            'item_part': txQtde,
            'volume_part': txVolume,
            'amount_vucv': amount_vucv, 
            'amount_weight': amount_weight,
            'amount_value_cl': amount_value_fob,
            'price_unit_cl': price_unit_fob,
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
            'desp_aduan_total': desp_aduan_total,
            'desp_aduan_part': desp_aduan_part,
            'desp_aduan_value': desp_aduan_value,
            'other_taxs_total': other_taxs_total,
            'other_taxs_part': other_taxs_part,
            'other_taxs_value': other_taxs_value,
            'cif_value': cif_value,
            'product_tot_value': round((cif_value + ii_valor), 2),
            'subtotal': subtotal,
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
            'icms_fator': icms_fator,
            'icms_aliquota': icms_aliquota,
            'icms_valor': icms_valor,
            'icms_st_base_calculo': icms_st_base_calculo,
            'icms_st_aliquota': icms_st_aliquota,
            'icms_st_valor': icms_st_valor,
            'price_cost': price_cost,
        }
        return vals

    @api.one
    @api.depends('product_id','quantity','price_vucv','amount_discount','weight_unit', 'volume_unit', 'tax_ii_id','tax_ipi_id',
                 'ipi_inclui_ii_base','tax_pis_id','tax_cofins_id','tax_icms_id','tax_icms_st_id', 'icms_fator_manual',
                 'icms_difer','icms_aliq_difer')
    def _compute_line(self):
        vlfreight = self.import_declaration_id.freight_value * self.import_declaration_id.tax_cambial
        vlInsurance = self.import_declaration_id.insurance_value * self.import_declaration_id.tax_cambial
        vlAfrmm = self.import_declaration_id.afrmm_value
        vlSiscomex = self.import_declaration_id.siscomex_value
        vlDespAdn = self.import_declaration_id.customs_value
        vlOther = self.import_declaration_id.other_value
        res = self.import_declaration_id._calc_ratio_di()
        # line.id, weight_part, value_part, volume_part, quant_part
        pw = res[self.name][self.sequence_addition][1]
        pv = res[self.name][self.sequence_addition][2]
        vv = res[self.name][self.sequence_addition][3]
        pq = res[self.name][self.sequence_addition][4]
        vals = self._calcule_line(pw,pv,pq,vv,vlfreight,vlInsurance,vlAfrmm,vlSiscomex,vlDespAdn,vlOther)
        self.update(vals)

    def _get_sequence(self):
        return '001'
    
    import_declaration_id = fields.Many2one('br_account.import.declaration', 'DI', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='import_declaration_id.company_id', readonly=True)
    currency_id = fields.Many2one('res.currency', related='import_declaration_id.currency_id', readonly=True)
    currency_purchase_id = fields.Many2one('res.currency', related='import_declaration_id.currency_purchase_id', readonly=True)
    tax_cambial = fields.Float(related='import_declaration_id.tax_cambial', readonly=True, store=True)
    
    name = fields.Char('Adição', size=3, required=True)
    sequence_addition = fields.Char('Sequencia', size=3, required=True, default=_get_sequence)
    product_id = fields.Many2one('product.product', string='Produto', ondelete='restrict', index=True)
    manufacturer_code = fields.Char('Código Fabricante', size=60)
    manufacturer_description = fields.Char('Descrição Fabricante')
    uom_id = fields.Many2one('product.uom', string='UM', ondelete='set null', index=True)
    quantity = fields.Float(string='Qtde.', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1)
    discount = fields.Float(string='% Desconto', digits=dp.get_precision('Discount'), default=0.00)
    amount_discount = fields.Float(string='Desconto', digits=(12,4), default=0.00)
    price_vucv = fields.Float(string='VUCV', required=True, digits=(18,7), default=0.00, oldname='price_unit')
    weight_unit = fields.Float(string='Peso Un Liq (kg)', required=True, digits=(12,4), default=0.00)
    volume_unit = fields.Float(string='Volume (m³)', required=True, digits=(18,6), default=0.00)

    weight_part = fields.Float(string='% Peso Liq', digits=(12,4), compute='_compute_line', readonly=True, store=True)
    value_part = fields.Float(string='% Valor FOB', digits=(12,4), compute='_compute_line', readonly=True, store=True)
    item_part = fields.Float(string='% Qtde', digits=(12,4), compute='_compute_line', readonly=True, store=True)
    volume_part = fields.Float(string='% Volume', digits=(12,4), compute='_compute_line', readonly=True, store=True)

    # Fileds Calculados
    amount_vucv = fields.Float(string='VUCV FOB', compute='_compute_line', digits=(12,2), readonly=True, store=True, oldname='amount_value')
    amount_value_cl = fields.Float(string='Valor FOB', compute='_compute_line', digits=(12,2), readonly=True, store=True)
    price_unit_cl = fields.Float(string='Preço Un', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)
    amount_weight = fields.Float(string='Peso Liq (kg)', compute='_compute_line', digits=(12,4), readonly=True, store=True)

    freight_total = fields.Float(string='Frete Vl.', compute='_compute_line', digits=(12,2), readonly=True, store=True)
    freight_part = fields.Float(string='Frete %', compute='_compute_line', digits=(12,6), readonly=True, store=True)
    freight_value = fields.Float(string='Frete', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)
    
    insurance_total = fields.Float(string='Seguro Vl.', compute='_compute_line', digits=(12,2), readonly=True, store=True)
    insurance_part = fields.Float(string='Seguro %', compute='_compute_line', digits=(12,7), readonly=True, store=True)
    insurance_value = fields.Float(string='Seguro', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)

    afrmm_total = fields.Float(string='AFRMM Vl.', compute='_compute_line', digits=(12,2), readonly=True, store=True)
    afrmm_part = fields.Float(string='AFRMM %', compute='_compute_line', digits=(12,7), readonly=True, store=True)
    afrmm_value = fields.Float(string='AFRMM', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)

    siscomex_total = fields.Float(string='SISCOMEX Vl.', compute='_compute_line', digits=(12,2), readonly=True, store=True)
    siscomex_part = fields.Float(string='SISCOMEX %', compute='_compute_line', digits=(12,7), readonly=True, store=True)
    siscomex_value = fields.Float(string='SISCOMEX', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)

    desp_aduan_total = fields.Float(string='Desp. Aduana Vl.', compute='_compute_line', digits=(12,2), readonly=True, store=True)
    desp_aduan_part = fields.Float(string='Desp. Aduana %', compute='_compute_line', digits=(12,7), readonly=True, store=True)
    desp_aduan_value = fields.Float(string='Desp. Aduana', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)

    other_taxs_total = fields.Float(string='Outras Taxas Vl.', compute='_compute_line', digits=(12,2), readonly=True, store=True)
    other_taxs_part = fields.Float(string='Outras Taxas %', compute='_compute_line', digits=(12,7), readonly=True, store=True)
    other_taxs_value = fields.Float(string='Outras Taxas', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)

    cif_value = fields.Float(string='Valor CIF', compute='_compute_line', digits=(12,2), readonly=True, store=True)
    product_tot_value = fields.Float(string='Valor CIF+AFRMM', compute='_compute_line', digits=(12,2), readonly=True, store=True, oldname='cif_afrmm_value')
    subtotal = fields.Float(string='SubTotal', compute='_compute_line', digits=(12,2), readonly=True, store=True)

    price_unit_edoc = fields.Float(string='Preço Un eDoc', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)
    
    price_cost = fields.Float(string='Preço Custo Calc', compute='_compute_line', digits=dp.get_precision('Product Price'), readonly=True, store=True)

    # impostos
    # II
    tax_ii_id = fields.Many2one('account.tax', string="Alíquota II", domain=[('domain', '=', 'ii'),('type_tax_use','=','purchase')])
    ii_base_calculo = fields.Float('Base II', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00, store=True)
    ii_aliquota = fields.Float('II %', compute='_compute_line', digits=(12,4), default=0.00, store=True)
    ii_valor = fields.Float('Valor II', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line', store=True)
    
    # IPI
    tax_ipi_id = fields.Many2one('account.tax', string="Alíquota IPI", domain=[('domain', '=', 'ipi'),('type_tax_use','=','purchase')])
    ipi_inclui_ii_base = fields.Boolean('Inclui II na base',default=True)
    ipi_base_calculo = fields.Float('Base IPI', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00, store=True)
    ipi_aliquota = fields.Float('IPI %', compute='_compute_line', digits=(12,4), default=0.00, store=True)
    ipi_valor = fields.Float('Valor IPI', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line', store=True)

    # PIS
    tax_pis_id = fields.Many2one('account.tax', string="Alíquota PIS", domain=[('domain', '=', 'pis'),('type_tax_use','=','purchase')])
    pis_base_calculo = fields.Float('Base PIS', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00, store=True)
    pis_aliquota = fields.Float('PIS %', compute='_compute_line', digits=(12,4), default=0.00, store=True)
    pis_valor = fields.Float('Valor PIS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line', store=True)

    # COFINS
    tax_cofins_id = fields.Many2one('account.tax', string="Alíquota COFINS", domain=[('domain', '=', 'cofins'),('type_tax_use','=','purchase')])
    cofins_base_calculo = fields.Float('Base COFINS', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00, store=True)
    cofins_aliquota = fields.Float('COFINS %', compute='_compute_line', digits=(12,4), default=0.00, store=True)
    cofins_valor = fields.Float('Valor COFINS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line', store=True)

    # ICMS
    tax_icms_id = fields.Many2one('account.tax', string="Alíquota ICMS", domain=[('domain', '=', 'icms'),('type_tax_use','=','purchase')])
    icms_base_calculo = fields.Float('Base ICMS', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00, store=True)
    icms_fator = fields.Float('ICMS Fator', compute='_compute_line', digits=(12,4), default=0.00, store=True)
    icms_fator_manual = fields.Float('ICMS Fator Manual', digits=(12,4), default=0.00)
    icms_aliquota = fields.Float('ICMS %', compute='_compute_line', digits=(12,4), default=0.00, store=True)
    icms_valor = fields.Float('Valor ICMS', digits=dp.get_precision('Account'),default=0.00, compute='_compute_line', store=True)
    icms_difer = fields.Boolean('Diferimento?')
    icms_aliq_difer = fields.Float('Diferimento %', digits=(12,4), default=0.00)

    # ICMS ST
    tax_icms_st_id = fields.Many2one('account.tax', string="Alíquota ICMS ST", domain=[('domain', '=', 'icmsst'),('type_tax_use','=','purchase')])
    icms_st_base_calculo = fields.Float('Base ICMS ST', compute='_compute_line', digits=dp.get_precision('Account'), default=0.00, store=True)
    icms_st_aliquota = fields.Float('ICMS ST %', compute='_compute_line', digits=(12,4), default=0.00, store=True)
    icms_st_valor = fields.Float('Valor ICMS ST', compute='_compute_line', digits=dp.get_precision('Account'),default=0.00, store=True)

    drawback_number = fields.Char('Número Drawback', size=11)

    @api.onchange('discount')
    def _onchange_discount(self):
        amount_vucv = self.quantity * self.price_vucv
        disc_vl = amount_vucv * (self.discount/100) if self.discount > 0.0 else 0.0
        if disc_vl != self.amount_discount:
            self.amount_discount = disc_vl
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if bool(self.product_id):
            partner = self.import_declaration_id.partner_id
            self.ipi_inclui_ii_base = True
            self.weight_unit = self.product_id.weight
            self.volume_unit = self.product_id.volume
            self.uom_id = self.product_id.uom_id
            suplierinfo = self.env['product.supplierinfo']
            if bool(partner):
                suplierinfo = suplierinfo.search([('name','=',partner.id),('product_tmpl_id','=',self.product_id.product_tmpl_id.id)],limit=1)
            self.manufacturer_code = suplierinfo.product_code or self.product_id.code
            self.manufacturer_description = suplierinfo.product_name or self.product_id.name
            fpos = self.import_declaration_id.fiscal_position_id or self.import_declaration_id.partner_id.property_purchase_fiscal_position_id
            if fpos:
                vals = fpos.map_tax_extra_values(self.product_id, self.import_declaration_id.partner_id, self.product_id.fiscal_classification_id, False, False, False)
                self.tax_ii_id = vals.get('tax_ii_id',False)
                self.tax_ipi_id = vals.get('tax_ipi_id',False)
                self.tax_pis_id = vals.get('tax_pis_id',False)
                self.tax_cofins_id = vals.get('tax_cofins_id',False)
                self.tax_icms_id = vals.get('tax_icms_id',False)
                self.tax_icms_st_id = vals.get('tax_icms_st_id',False)

#     @api.constrains('name', 'sequence_addition')
#     def _check_name_sequence(self):
#         for line in self.import_declaration_id.line_ids:
#             if line.id != self.id:
#                 if line.name == self.name and line.sequence_addition == self.sequence_addition:
#                     raise UserError('Mesmo número de sequencia para a adição.')
                    
