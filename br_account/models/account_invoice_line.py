import logging

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from .cst import CST_ICMS
from .cst import CSOSN_SIMPLES
from .cst import CST_IPI
from .cst import CST_PIS_COFINS
from .cst import ORIGEM_PROD
from .res_company import COMPANY_FISCAL_TYPE

_logger = logging.getLogger(__name__)

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _default_company_fiscal_type(self):
        if self.invoice_id:
            return self.invoice_id.company_id.fiscal_type
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        return company.fiscal_type

    def _prepare_tax_context(self):
        return {
            'incluir_ipi_base': self.incluir_ipi_base,
            'icms_st_aliquota_mva': self.icms_st_aliquota_mva,
            'icms_aliquota_reducao_base': self.icms_aliquota_reducao_base,
            'icms_st_aliquota_reducao_base': self.icms_st_aliquota_reducao_base,
            'icms_aliquota_diferimento': self.icms_aliquota_diferimento,
            'icms_st_aliquota_deducao': self.icms_st_aliquota_deducao,
            'icms_st_base_calculo_manual': self.icms_st_base_calculo_manual,
            'ipi_reducao_bc': self.ipi_reducao_bc,
            'icms_base_calculo': self.icms_base_calculo,
            'icms_base_calculo_manual': self.icms_base_calculo_manual,
            'ipi_base_calculo': self.ipi_base_calculo,
            'ipi_base_calculo_manual': self.ipi_base_calculo_manual,
            'pis_base_calculo': self.pis_base_calculo,
            'pis_base_calculo_manual': self.pis_base_calculo_manual,
            'cofins_base_calculo': self.cofins_base_calculo,
            'cofins_base_calculo_manual': self.cofins_base_calculo_manual,
            'ii_base_calculo': self.ii_base_calculo,
            'issqn_base_calculo': self.issqn_base_calculo,
            'icms_aliquota_inter_part': self.icms_aliquota_inter_part,
            'l10n_br_issqn_deduction': self.l10n_br_issqn_deduction,
        }

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id',
                 'invoice_id.currency_id', 'invoice_id.company_id',
                 'tax_icms_id', 'tax_icms_st_id', 'tax_icms_inter_id',
                 'tax_icms_intra_id', 'tax_icms_fcp_id', 'tax_ipi_id',
                 'tax_pis_id', 'tax_cofins_id', 'tax_ii_id', 'tax_issqn_id',
                 'tax_csll_id', 'tax_irrf_id', 'tax_inss_id', 'tax_outros_id',
                 'incluir_ipi_base', 'tem_difal', 'icms_aliquota_reducao_base',
                 'ipi_reducao_bc', 'icms_st_aliquota_mva', 'icms_aliquota_diferimento',
                 'icms_st_aliquota_reducao_base', 'icms_aliquota_credito',
                 'icms_st_aliquota_deducao', 'icms_st_base_calculo_manual',
                 'icms_base_calculo_manual', 'ipi_base_calculo_manual',
                 'pis_base_calculo_manual', 'cofins_base_calculo_manual',
                 'icms_st_aliquota_deducao', 'ii_base_calculo',
                 'icms_aliquota_inter_part', 'l10n_br_issqn_deduction')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
 
        valor_bruto = self.price_unit * self.quantity
        desconto = valor_bruto * self.discount / 100.0
        subtotal = valor_bruto - desconto
        taxes = False
        self._update_invoice_line_ids()
        if self.invoice_line_tax_ids:
            ctx = self._prepare_tax_context()
 
            tax_ids = self.invoice_line_tax_ids.with_context(**ctx)
 
            taxes = tax_ids.compute_all(
                price, currency, self.quantity, product=self.product_id,
                partner=self.invoice_id.partner_id)
 
        icms = ([x for x in taxes['taxes']
                 if x['id'] == self.tax_icms_id.id]) if taxes else []
        icmsst = ([x for x in taxes['taxes']
                   if x['id'] == self.tax_icms_st_id.id]) if taxes else []
        icms_inter = (
            [x for x in taxes['taxes']
             if x['id'] == self.tax_icms_inter_id.id]) if taxes else []
        icms_intra = (
            [x for x in taxes['taxes']
             if x['id'] == self.tax_icms_intra_id.id]) if taxes else []
        icms_fcp = ([x for x in taxes['taxes']
                     if x['id'] == self.tax_icms_fcp_id.id]) if taxes else []
        ipi = ([x for x in taxes['taxes']
                if x['id'] == self.tax_ipi_id.id]) if taxes else []
        pis = ([x for x in taxes['taxes']
                if x['id'] == self.tax_pis_id.id]) if taxes else []
        cofins = ([x for x in taxes['taxes']
                   if x['id'] == self.tax_cofins_id.id]) if taxes else []
        issqn = ([x for x in taxes['taxes'] if x['id'] == self.tax_issqn_id.id]) if taxes else []
        
        ii = ([x for x in taxes['taxes']
               if x['id'] == self.tax_ii_id.id]) if taxes else []
        csll = ([x for x in taxes['taxes']
                 if x['id'] == self.tax_csll_id.id]) if taxes else []
        irrf = ([x for x in taxes['taxes']
                 if x['id'] == self.tax_irrf_id.id]) if taxes else []
        inss = ([x for x in taxes['taxes']
                 if x['id'] == self.tax_inss_id.id]) if taxes else []
        outros = ([x for x in taxes['taxes']
                if x['id'] == self.tax_outros_id.id]) if taxes else []
 
        price_subtotal_signed = taxes['total_excluded'] if taxes else subtotal
        if self.invoice_id.currency_id and self.invoice_id.currency_id != \
           self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.compute(
                price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
 
        if self.icms_aliquota_credito:
            # Calcular o valor da base_icms para o calculo de
            # credito de ICMS
            ctx = self._prepare_tax_context()
            valor_frete = ctx.get('valor_frete', 0.0)
            valor_seguro = ctx.get('valor_seguro', 0.0)
            outras_despesas = ctx.get('outras_despesas', 0.0)
 
            base_icms_credito = subtotal + valor_frete \
                + valor_seguro + outras_despesas
        else:
            base_icms_credito = 0.0
 
        price_subtotal_signed = price_subtotal_signed * sign
        dif_icms_dif = (self.icms_valor - self.icms_valor_diferido)
        self.update({
            'price_total': taxes['total_included'] if taxes else subtotal,
            'price_tax': taxes['total_included'] - taxes['total_excluded']
            if taxes else 0,
            'price_subtotal': taxes['total_excluded'] if taxes else subtotal,
            'price_subtotal_signed': price_subtotal_signed,
            'valor_bruto': self.quantity * self.price_unit,
            'valor_desconto': desconto,
            'icms_base_calculo': sum([x['base'] for x in icms]),
            'icms_valor': sum([x['amount'] for x in icms]),
            'icms_aliquota': sum([self.env['account.tax'].browse([x['id']]).amount for x in icms]) / len(icms) if len(icms) > 0 else 0.0,
            'icms_valor_diferido': sum([x['operacao'] for x in icms]),
            'icms_st_base_calculo': sum([x['base'] for x in icmsst]),
            'icms_st_valor': sum([x['amount'] for x in icmsst]),
            'icms_bc_uf_dest': sum([x['base'] for x in icms_inter]),
            'icms_uf_remet': sum([x['amount'] for x in icms_inter]),
            'icms_uf_dest': sum([x['amount'] for x in icms_intra]),
            'icms_fcp_uf_dest': sum([x['amount'] for x in icms_fcp]),
            'icms_valor_credito': base_icms_credito * (self.icms_aliquota_credito / 100),
            'ipi_base_calculo': sum([x['base'] for x in ipi]),
            'ipi_valor': sum([x['amount'] for x in ipi]),
            'ipi_aliquota': sum([self.env['account.tax'].browse([x['id']]).amount for x in ipi]) / len(ipi) if len(ipi) > 0 else 0.0,
            'pis_base_calculo': sum([x['base'] for x in pis]),
            'pis_valor': sum([x['amount'] for x in pis]),
            'pis_aliquota': sum([self.env['account.tax'].browse([x['id']]).amount for x in pis]) / len(pis) if len(pis) > 0 else 0.0,
            'cofins_base_calculo': sum([x['base'] for x in cofins]),
            'cofins_valor': sum([x['amount'] for x in cofins]),
            'cofins_aliquota': sum([self.env['account.tax'].browse([x['id']]).amount for x in cofins]) / len(cofins) if len(cofins) > 0 else 0.0,
            'issqn_base_calculo': sum([x['base'] for x in issqn]),
            'issqn_valor': sum([x['amount'] for x in issqn]),
            'issqn_aliquota': sum([self.env['account.tax'].browse([x['id']]).amount for x in issqn]) / len(issqn) if len(issqn) > 0 else 0.0,#sum([self.env['account.tax'].browse([x['id']]).amount for x in issqn]),
            'ii_base_calculo': sum([x['base'] for x in ii]),
            'ii_valor': sum([x['amount'] for x in ii]),
            'csll_base_calculo': sum([x['base'] for x in csll]),
            'csll_valor': sum([x['amount'] for x in csll]),
            'inss_base_calculo': sum([x['base'] for x in inss]),
            'inss_valor': sum([x['amount'] for x in inss]),
            'irrf_base_calculo': sum([x['base'] for x in irrf]),
            'irrf_valor': sum([x['amount'] for x in irrf]),
            'outros_base_calculo': sum([x['base'] for x in outros]),
            'outros_valor': sum([x['amount'] for x in outros]),
            'icms_valor_diferido_dif': dif_icms_dif*-1 if dif_icms_dif < 0 else dif_icms_dif,
        })

    @api.multi
    @api.depends('icms_cst_normal', 'icms_csosn_simples',
                 'company_fiscal_type')
    def _compute_cst_icms(self):
        for item in self:
            item.icms_cst = item.icms_cst_normal \
                if item.company_fiscal_type == '3' else item.icms_csosn_simples

    def _render_name(self):
        res = False
        if bool(self.product_id.description_fiscal):
            try:
                res = self.product_id.render_template(self.product_id.description_fiscal,invoice=self.invoice_id,line=self)
            except:
                pass
        return res

    price_tax = fields.Float(
        compute='_compute_price', string='Impostos', store=True,
        digits=dp.get_precision('Account'))
    price_total = fields.Float(
        'Valor Líquido', digits=dp.get_precision('Account'), store=True,
        default=0.00, compute='_compute_price')
    valor_desconto = fields.Float(
        string='Vlr. desconto', store=True, compute='_compute_price',
        digits=dp.get_precision('Account'))
    valor_bruto = fields.Float(
        string='Vlr. Bruto', store=True, compute='_compute_price',
        digits=dp.get_precision('Account'))
    tributos_estimados = fields.Float(
        string='Total Est. Tributos', default=0.00,
        digits=dp.get_precision('Account'))
    tributos_estimados_federais = fields.Float(
        string='Tributos Federais', default=0.00,
        digits=dp.get_precision('Account'))
    tributos_estimados_estaduais = fields.Float(
        string='Tributos Estaduais', default=0.00,
        digits=dp.get_precision('Account'))
    tributos_estimados_municipais = fields.Float(
        string='Tributos Municipais', default=0.00,
        digits=dp.get_precision('Account'))

    rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    cfop_id = fields.Many2one('br_account.cfop', 'CFOP')
    fiscal_classification_id = fields.Many2one('product.fiscal.classification', 'Classificação Fiscal')
    product_type = fields.Selection(related='product_id.fiscal_type', store=True)
    company_fiscal_type = fields.Selection(COMPANY_FISCAL_TYPE, default=_default_company_fiscal_type, string="Regime Tributário")
    calculate_tax = fields.Boolean(string="Calcular Imposto?", default=True)
    fiscal_comment = fields.Text('Observação Fiscal')

    # =========================================================================
    # ICMS Normal
    # =========================================================================
    icms_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_icms_id = fields.Many2one('account.tax', string="Alíquota ICMS",
                                  domain=[('domain', '=', 'icms')])
    icms_cst = fields.Char('CST ICMS', size=10,
                           store=True, compute='_compute_cst_icms')
    icms_cst_normal = fields.Selection(CST_ICMS, string="CST ICMS")
    icms_origem = fields.Selection(ORIGEM_PROD, 'Origem', default='0')
    icms_benef = fields.Many2one('br_account.beneficio.fiscal', string="Benificio Fiscal")
    icms_tipo_base = fields.Selection(
        [('0', '0 - Margem Valor Agregado (%)'),
         ('1', '1 - Pauta (valor)'),
         ('2', '2 - Preço Tabelado Máximo (valor)'),
         ('3', '3 - Valor da Operação')],
        'Tipo Base ICMS', required=True, default='3')
    incluir_ipi_base = fields.Boolean(
        string="Incl. Valor IPI?",
        help="Se marcado o valor do IPI inclui a base de cálculo")
    icms_base_calculo = fields.Float(
        'Base ICMS', required=True, compute='_compute_price', store=True,
        digits=dp.get_precision('Account'), default=0.00)
    icms_valor = fields.Float(
        'Valor ICMS', required=True, compute='_compute_price', store=True,
        digits=dp.get_precision('Account'), default=0.00)
    icms_aliquota = fields.Float(
        'ICMS %', digits=(12,4), default=0.00)
    icms_aliquota_reducao_base = fields.Float(
        'Red. Base ICMS %', digits=(12,4),
        default=0.00)
    icms_base_calculo_manual = fields.Float(
        'Base ICMS Manual', digits=dp.get_precision('Account'), default=0.00)

    # =========================================================================
    # ICMS Diferido
    # =========================================================================

    icms_aliquota_diferimento = fields.Float("Diferimento %", digits=(12,4), default=0.0)
    icms_valor_diferido = fields.Float('Vl ICMS diferido', required=True, compute='_compute_price', store=True, digits=dp.get_precision('Account'), default=0.00)
    icms_valor_diferido_dif = fields.Float('Vl diferenca ICMS diferido', compute='_compute_price',store=True, digits=dp.get_precision('Account'), default=0.00)

    # =========================================================================
    # ICMS Substituição
    # =========================================================================
    tax_icms_st_id = fields.Many2one('account.tax', string="Alíquota ICMS ST", domain=[('domain', '=', 'icmsst')])
    icms_st_tipo_base = fields.Selection(
        [('0', '0 - Preço tabelado ou máximo  sugerido'),
         ('1', '1 - Lista Negativa (valor)'),
         ('2', '2 - Lista Positiva (valor)'),
         ('3', '3 - Lista Neutra (valor)'),
         ('4', '4 - Margem Valor Agregado (%)'),
         ('5', '5 - Pauta (valor)'),
         ('6', '6 - Valor da Operação')],
        'Tipo Base ICMS ST', required=True, default='4')
    icms_st_valor = fields.Float('Valor ICMS ST', required=True, compute='_compute_price', store=True, digits=dp.get_precision('Account'), default=0.00)
    icms_st_base_calculo = fields.Float('Base ICMS ST', required=True, compute='_compute_price', store=True,digits=dp.get_precision('Account'), default=0.00)
    icms_st_aliquota = fields.Float('ICMS ST %', digits=(12,4), default=0.00, compute='_compute_price', store=True)
    icms_st_aliquota_reducao_base = fields.Float('Red. Base ST %',digits=(12,4),default=0.00)
    icms_st_aliquota_mva = fields.Float('MVA Ajustado ST %',digits=(12,4), default=0.00)
    icms_st_base_calculo_manual = fields.Float('Base ICMS ST Manual', digits=(12,4),default=0.00)

    # =========================================================================
    # ICMS Difal
    # =========================================================================
    tem_difal = fields.Boolean('Difal?')
    icms_bc_uf_dest = fields.Float('Base ICMS', compute='_compute_price',digits=dp.get_precision('Account'))
    tax_icms_inter_id = fields.Many2one('account.tax', help="Alíquota utilizada na operação Interestadual",string="ICMS Inter", domain=[('domain', '=', 'icms_inter')])
    tax_icms_intra_id = fields.Many2one('account.tax', help="Alíquota interna do produto no estado destino",string="ICMS Intra", domain=[('domain', '=', 'icms_intra')])
    tax_icms_fcp_id = fields.Many2one('account.tax', string="% FCP", domain=[('domain', '=', 'fcp')])
    icms_aliquota_inter_part = fields.Float('% Partilha', default=0.0, digits=(12,4))
    icms_fcp_uf_dest = fields.Float(string='Valor FCP', compute='_compute_price',digits=dp.get_precision('Account'))
    icms_uf_dest = fields.Float('ICMS Destino', compute='_compute_price',digits=dp.get_precision('Account'))
    icms_uf_remet = fields.Float('ICMS Remetente', compute='_compute_price',digits=dp.get_precision('Account'))

    # =========================================================================
    # ICMS Simples Nacional
    # =========================================================================
    icms_csosn_simples = fields.Selection(CSOSN_SIMPLES, string="CSOSN ICMS")
    icms_aliquota_credito = fields.Float("% Crédito ICMS", digits=(12,4))
    icms_valor_credito = fields.Float("Valor de Crédito", compute='_compute_price', digits=dp.get_precision('Account'), store=True)
    icms_st_aliquota_deducao = fields.Float(string="% ICMS Próprio", digits=(12,4), help="Alíquota interna ou interestadual aplicada \
                                                                                          sobre o valor da operação para deduzir do ICMS ST - Para empresas \
                                                                                          do Simples Nacional ou usado em casos onde existe apenas ST sem ICMS")

    # =========================================================================
    # ICMS Retido anteriormente por ST
    # =========================================================================

    icms_substituto = fields.Monetary("ICMS Substituto", digits=dp.get_precision('Account'), oldname='icms_st_substituto', 
                                      help='Valor do ICMS Próprio do Substituto cobrado em operação anterior')
    icms_bc_st_retido = fields.Monetary("Base Calc. ST Ret.", digits=dp.get_precision('Account'), oldname='icms_st_bc_ret_ant',
                                        help='Valor da BC do ICMS ST cobrado anteriormente por ST (v2.0).')
    icms_aliquota_st_retido = fields.Float("% ST Retido", digits=(12,4), oldname='icms_st_ali_sup_cons',
                                           help='Deve ser informada a alíquota do cálculo do ICMS-ST, já incluso o FCP caso incida sobre a mercadoria')
    icms_st_retido = fields.Monetary("ICMS ST Ret.", digits=dp.get_precision('Account'), oldname='icms_st_ret_ant', 
                                     help='Valor do ICMS ST cobrado anteriormente por ST (v2.0).')

    # =========================================================================
    # ISSQN
    # =========================================================================
    issqn_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_issqn_id = fields.Many2one('account.tax', string="Alíquota ISSQN", domain=[('domain', '=', 'issqn')])
    issqn_tipo = fields.Selection([('N', 'Normal'),
                                   ('R', 'Retida'),
                                   ('S', 'Substituta'),
                                   ('I', 'Isenta')],
                                  string='Tipo do ISSQN',
                                  required=True, default='N')
    service_type_id = fields.Many2one('br_account.service.type', 'Tipo de Serviço')
    issqn_base_calculo = fields.Float('Base ISSQN', digits=dp.get_precision('Account'),compute='_compute_price', store=True)
    issqn_aliquota = fields.Float('ISSQN %', required=True, digits=(12,4),default=0.00,compute='_compute_price', store=True)
    issqn_valor = fields.Float('Valor ISSQN', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True)
    l10n_br_issqn_deduction = fields.Float('% Dedução Base ISSQN', digits=(12,4), default=0.00, store=True)

    # =========================================================================
    # IPI
    # =========================================================================
    ipi_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_ipi_id = fields.Many2one('account.tax', string="Alíquota IPI", domain=[('domain', '=', 'ipi')])
    ipi_tipo = fields.Selection([('percent', 'Percentual')], 'Tipo do IPI', required=True, default='percent')
    ipi_base_calculo = fields.Float('Base IPI', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True,)
    ipi_reducao_bc = fields.Float('Redução Base %', required=True, digits=(12,4),default=0.00)
    ipi_valor = fields.Float('Valor IPI', required=True, digits=dp.get_precision('Account'),default=0.00, compute='_compute_price', store=True)
    ipi_aliquota = fields.Float('IPI %', digits=(12,4), default=0.00, compute='_compute_price', store=True)
    ipi_cst = fields.Selection(CST_IPI, string='CST IPI')
    ipi_base_calculo_manual = fields.Float('Base IPI Manual', digits=dp.get_precision('Account'), default=0.00)
    ipi_codigo_enquadramento = fields.Many2one('br_account.enquadramento.ipi', 'Cod.Enquadramento')
    ipi_classe_enquadramento = fields.Char(string="Clas.Enquadram.", size=5)

    # =========================================================================
    # PIS
    # =========================================================================
    pis_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_pis_id = fields.Many2one('account.tax', string="Alíquota PIS", domain=[('domain', '=', 'pis')])
    pis_cst = fields.Selection(CST_PIS_COFINS, 'CST PIS')
    pis_tipo = fields.Selection([('percent', 'Percentual')], string='Tipo do PIS', required=True, default='percent')
    pis_base_calculo = fields.Float('Base PIS', required=True, compute='_compute_price', store=True, digits=dp.get_precision('Account'), default=0.00)
    pis_valor = fields.Float('Valor PIS', required=True, digits=dp.get_precision('Account'),default=0.00, compute='_compute_price', store=True)
    pis_aliquota = fields.Float('PIS %', digits=(12,4), default=0.00, compute='_compute_price', store=True)
    pis_base_calculo_manual = fields.Float('Base PIS Manual', digits=dp.get_precision('Account'), default=0.00)

    # =========================================================================
    # COFINS
    # =========================================================================
    cofins_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_cofins_id = fields.Many2one('account.tax', string="Alíquota COFINS", domain=[('domain', '=', 'cofins')])
    cofins_cst = fields.Selection(CST_PIS_COFINS, 'CST COFINS')
    cofins_tipo = fields.Selection([('percent', 'Percentual')], string='Tipo do COFINS', required=True, default='percent')
    cofins_base_calculo = fields.Float('Base COFINS', compute='_compute_price', store=True, digits=dp.get_precision('Account'))
    cofins_valor = fields.Float('Valor COFINS', digits=dp.get_precision('Account'), compute='_compute_price', store=True)
    cofins_aliquota = fields.Float('COFINS %', digits=(12,4), default=0.00, compute='_compute_price', store=True)
    cofins_base_calculo_manual = fields.Float('Base COFINS Manual', digits=dp.get_precision('Account'), default=0.00)

    # =========================================================================
    # Imposto de importação
    # =========================================================================
    ii_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_ii_id = fields.Many2one('account.tax', string="Alíquota II", domain=[('domain', '=', 'ii')])
    ii_base_calculo = fields.Float('Base II', required=True, digits=dp.get_precision('Account'), default=0.00, store=True)
    ii_aliquota = fields.Float('II %', required=True, digits=(12,4), default=0.00)
    ii_valor = fields.Float('Valor II', required=True, digits=dp.get_precision('Account'),default=0.00, compute='_compute_price', store=True)
    ii_valor_iof = fields.Float('Valor IOF', required=True, digits=dp.get_precision('Account'),default=0.00)
    ii_valor_despesas = fields.Float('Desp. Aduaneiras', required=True,digits=dp.get_precision('Account'), default=0.00)
    import_declaration_ids = fields.Many2many('br_account.import.declaration', string='Declaração de Importação')

    # =========================================================================
    # Impostos de serviço - CSLL
    # =========================================================================
    csll_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_csll_id = fields.Many2one('account.tax', string="Alíquota CSLL",domain=[('domain', '=', 'csll')])
    csll_base_calculo = fields.Float('Base CSLL', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True)
    csll_valor = fields.Float('Valor CSLL', required=True, digits=dp.get_precision('Account'),default=0.00, compute='_compute_price', store=True)
    csll_aliquota = fields.Float('Perc CSLL', required=True, digits=(12,4), default=0.00)

    # =========================================================================
    # Impostos de serviço - IRRF
    # =========================================================================
    irrf_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_irrf_id = fields.Many2one('account.tax', string="Alíquota IRRF", domain=[('domain', '=', 'irrf')])
    irrf_base_calculo = fields.Float('Base IRRF', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True)
    irrf_valor = fields.Float('Valor IRFF', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True)
    irrf_aliquota = fields.Float('IRRF %', required=True, digits=(12,4), default=0.00)

    # =========================================================================
    # Impostos de serviço - INSS
    # =========================================================================
    inss_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_inss_id = fields.Many2one('account.tax', string="Alíquota INSS", domain=[('domain', '=', 'inss')])
    inss_base_calculo = fields.Float('Base INSS', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True)
    inss_valor = fields.Float('Valor INSS', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True)
    inss_aliquota = fields.Float('INSS %', required=True, digits=(12,4),default=0.00)

    # =========================================================================
    # Impostos de serviço - Outras retenções
    # =========================================================================
    outros_rule_id = fields.Many2one('account.fiscal.position.tax.rule', 'Regra')
    tax_outros_id = fields.Many2one('account.tax', string="Alíquota Outras Ret.", domain=[('domain', '=', 'outros')])
    outros_base_calculo = fields.Float('Base Outras Ret.', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True)
    outros_valor = fields.Float('Valor Outras Ret.', required=True, digits=dp.get_precision('Account'), default=0.00, compute='_compute_price', store=True)
    outros_aliquota = fields.Float('Outros %', default=0.00, digits=(12,4), store=True)

    informacao_adicional = fields.Text(string="Informações Adicionais")

    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    @api.multi
    def _clear_tax_id(self):
        return {
            'icms_rule_id': False,
            'tax_icms_id': False,
            'icms_benef': False,
            'icms_tipo_base': '3',
            'incluir_ipi_base': False,
            'icms_aliquota': 0.00,
            'icms_aliquota_reducao_base': 0.00,
            'icms_base_calculo_manual': 0.00,
            'icms_aliquota_diferimento': 0.0,
            'tax_icms_st_id': False,
            'icms_st_tipo_base': '4',
            'icms_st_aliquota': 0.0,
            'icms_st_aliquota_reducao_base': 0.0,
            'icms_st_aliquota_mva': 0.0,
            'icms_st_base_calculo_manual': 0.0,
#             'icms_st_bc_ret_ant': 0.0, 
#             'icms_st_ali_sup_cons': 0.0, 
#             'icms_st_substituto': 0.0,
#             'icms_st_ret_ant': 0.0,
            "icms_substituto": 0.0,
            "icms_bc_st_retido": 0.0,
            "icms_aliquota_st_retido": 0.0,
            "icms_st_retido": 0.0,
            'tem_difal': False,
            'tax_icms_inter_id': False,
            'tax_icms_intra_id': False,
            'tax_icms_fcp_id': False,
            'icms_aliquota_inter_part': 0.0,
            'icms_aliquota_credito': 0.0,
            'icms_st_aliquota_deducao': 0.0,
            'issqn_rule_id': False,
            'tax_issqn_id': False,
            'issqn_tipo': 'N',
            'service_type_id': False,
            'issqn_aliquota': 0.00,
            'issqn_valor': 0.00,
            'l10n_br_issqn_deduction': 0.00,
            'ipi_rule_id': False,
            'tax_ipi_id': False,
            'ipi_tipo': 'percent',
            'ipi_reducao_bc': 0.00,
            'ipi_aliquota': 0.00,
            'ipi_cst': False,
            'ipi_base_calculo_manual': 0.00,
            'pis_rule_id': False,
            'tax_pis_id': False,
            'pis_cst': False,
            'pis_tipo': 'percent',
            'pis_aliquota': 0.00,
            'pis_base_calculo_manual': 0.00,
            'cofins_rule_id': False,
            'tax_cofins_id': False,
            'cofins_cst': False,
            'cofins_tipo': 'percent',
            'cofins_aliquota': 0.0,
            'cofins_base_calculo_manual': 0.0,
            'ii_rule_id': False,
            'tax_ii_id': False,
            'ii_base_calculo': 0.00,
            'ii_aliquota': 0.00,
            'ii_valor_iof': 0.00,
            'ii_valor_despesas': 0.00,
            'csll_rule_id': False,
            'tax_csll_id': False,
            'csll_aliquota': 0.00,
            'irrf_rule_id': False,
            'tax_irrf_id': False,
            'irrf_aliquota': 0.00,
            'inss_rule_id': False,
            'tax_inss_id': False,
            'inss_aliquota': 0.00,
            'outros_rule_id': False,
            'tax_outros_id': False,
            'outros_aliquota': 0.0,
            'invoice_line_tax_ids': [(5, 0, 0)]
        }

    @api.multi
    def clear_tax_id(self):
        for line in self:
            res = self._clear_tax_id()
            line.write(res)

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            line._update_tax_from_ncm()
            line._set_taxes_from_fiscal_pos()
            other_taxes = line.invoice_line_tax_ids.filtered(lambda x: not x.domain)
            line.invoice_line_tax_ids = line.tax_icms_id | line.tax_icms_st_id | \
                line.tax_icms_inter_id | line.tax_icms_intra_id | \
                line.tax_icms_fcp_id | line.tax_ipi_id | \
                line.tax_pis_id | line.tax_cofins_id | line.tax_issqn_id | \
                line.tax_ii_id | line.tax_csll_id | line.tax_irrf_id | \
                line.tax_inss_id | other_taxes
            line._compute_price()
            line._set_extimated_taxes(line.price_total)

    def _update_tax_from_ncm(self):
        if self.product_id:
            ncm = self.product_id.fiscal_classification_id
            self.update({
                'icms_st_aliquota_mva': ncm.icms_st_aliquota_mva,
                'icms_st_aliquota_reducao_base':
                ncm.icms_st_aliquota_reducao_base,
                'ipi_cst': ncm.ipi_cst,
                'ipi_reducao_bc': ncm.ipi_reducao_bc,
                'tax_icms_st_id': ncm.tax_icms_st_id.id,
                'tax_ipi_id': ncm.tax_ipi_id.id,
            })

    def _set_taxes_from_fiscal_pos(self):
        fpos = self.invoice_id.fiscal_position_id
        if fpos:
            vals = fpos.map_tax_extra_values(
                self.product_id, self.invoice_id.partner_id, self.fiscal_classification_id, 
                self.service_type_id, self.issqn_tipo, self.account_analytic_id)

            for key, value in vals.items():
                if value and key in self._fields:
                    self.update({key: value})

    def _set_taxes(self):
        for line in self:
            super(AccountInvoiceLine, line)._set_taxes()
            line._update_tax_from_ncm()
            line._set_taxes_from_fiscal_pos()
            other_taxes = line.invoice_line_tax_ids.filtered(lambda x: not x.domain)
            line.invoice_line_tax_ids = line.tax_icms_id | line.tax_icms_st_id | \
                line.tax_icms_inter_id | line.tax_icms_intra_id | \
                line.tax_icms_fcp_id | line.tax_ipi_id | \
                line.tax_pis_id | line.tax_cofins_id | line.tax_issqn_id | \
                line.tax_ii_id | line.tax_csll_id | line.tax_irrf_id | \
                line.tax_inss_id | other_taxes

    def _set_extimated_taxes(self, price):
        service = self.product_id.service_type_id
        ncm = self.product_id.fiscal_classification_id

        if self.product_type == 'service':
            self.tributos_estimados_federais = \
                price * (service.federal_nacional / 100)
            self.tributos_estimados_estaduais = \
                price * (service.estadual_imposto / 100)
            self.tributos_estimados_municipais = \
                price * (service.municipal_imposto / 100)
        else:
            federal = ncm.federal_nacional if self.icms_origem in \
                ('0', '3', '4', '5', '8') else ncm.federal_importado

            self.tributos_estimados_federais = price * (federal / 100)
            self.tributos_estimados_estaduais = \
                price * (ncm.estadual_imposto / 100)
            self.tributos_estimados_municipais = \
                price * (ncm.municipal_imposto / 100)

        self.tributos_estimados = self.tributos_estimados_federais + \
            self.tributos_estimados_estaduais + \
            self.tributos_estimados_municipais

    @api.onchange('price_subtotal')
    def _br_account_onchange_quantity(self):
        self._set_extimated_taxes(self.price_subtotal)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.issqn_tipo = 'N'
        domain = super(AccountInvoiceLine,self)._onchange_product_id()
        return domain
        
    @api.onchange('product_id')
    def _br_account_onchange_product_id(self):
        if len(self.product_id) > 0:
            self.product_type = self.product_id.fiscal_type
            self.icms_origem = self.product_id.origin
            ncm = self.product_id.fiscal_classification_id
            service = self.product_id.service_type_id
            self.fiscal_classification_id = ncm.id
            self.service_type_id = service.id
            self._set_extimated_taxes(self.product_id.lst_price)
            if self.product_id:
                self.account_analytic_id = self.invoice_id.account_analytic_id
                self.analytic_tag_ids = self.invoice_id.analytic_tag_ids

    @api.onchange('fiscal_classification_id','service_type_id','issqn_tipo','account_analytic_id')
    def _br_account_onchange_fiscal_values_id(self):
        if len(self.product_id) > 0:
            self._set_taxes()

    def _update_invoice_line_ids(self):
        other_taxes = self.invoice_line_tax_ids.filtered(
            lambda x: not x.domain)
        self.invoice_line_tax_ids = other_taxes | self.tax_icms_id | \
            self.tax_icms_st_id | self.tax_icms_inter_id | \
            self.tax_icms_intra_id | self.tax_icms_fcp_id | \
            self.tax_ipi_id | self.tax_pis_id | \
            self.tax_cofins_id | self.tax_issqn_id | self.tax_ii_id | \
            self.tax_csll_id | self.tax_irrf_id | self.tax_inss_id | \
            self.tax_outros_id

    @api.onchange('tax_icms_id')
    def _onchange_tax_icms_id(self):
        if self.tax_icms_id:
            self.icms_aliquota = self.tax_icms_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_icms_st_id')
    def _onchange_tax_icms_st_id(self):
        if self.tax_icms_st_id:
            self.icms_st_aliquota = self.tax_icms_st_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_icms_inter_id')
    def _onchange_tax_icms_inter_id(self):
        self._update_invoice_line_ids()

    @api.onchange('tax_icms_intra_id')
    def _onchange_tax_icms_intra_id(self):
        self._update_invoice_line_ids()

    @api.onchange('tax_icms_fcp_id')
    def _onchange_tax_icms_fcp_id(self):
        self._update_invoice_line_ids()

    @api.onchange('tax_pis_id')
    def _onchange_tax_pis_id(self):
        if self.tax_pis_id:
            self.pis_aliquota = self.tax_pis_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_cofins_id')
    def _onchange_tax_cofins_id(self):
        if self.tax_cofins_id:
            self.cofins_aliquota = self.tax_cofins_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_ipi_id')
    def _onchange_tax_ipi_id(self):
        if self.tax_ipi_id:
            self.ipi_aliquota = self.tax_ipi_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_ii_id')
    def _onchange_tax_ii_id(self):
        if self.tax_ii_id:
            self.ii_aliquota = self.tax_ii_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_issqn_id')
    def _onchange_tax_issqn_id(self):
        if self.tax_issqn_id:
            self.issqn_aliquota = self.tax_issqn_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_csll_id')
    def _onchange_tax_csll_id(self):
        if self.tax_csll_id:
            self.csll_aliquota = self.tax_csll_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_irrf_id')
    def _onchange_tax_irrf_id(self):
        if self.tax_irrf_id:
            self.irrf_aliquota = self.tax_irrf_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_inss_id')
    def _onchange_tax_inss_id(self):
        if self.tax_inss_id:
            self.inss_aliquota = self.tax_inss_id.amount
        self._update_invoice_line_ids()

    @api.onchange('tax_outros_id')
    def _onchange_tax_outros_id(self):
        if self.tax_outros_id:
            self.outros_aliquota = self.tax_outros_id.amount
        self._update_invoice_line_ids()

    @api.onchange('product_id','quantity','uom_id','price_unit','discount','tributos_estimados',
                  'tributos_estimados_federais','tributos_estimados_estaduais','tributos_estimados_municipais')
    def _onchange_name(self):
        res = self._render_name()
        if bool(res):
            self.name = res

    def _mount_tax_ids(self):
        res = []
        self._set_taxes()
        other_taxes = self.invoice_line_tax_ids.filtered(lambda x: not x.domain)
        for tax in other_taxes:
            res.append(tax.id)
        if self.tax_icms_id: res.append(self.tax_icms_id.id)
        if self.tax_icms_st_id: res.append(self.tax_icms_st_id.id)
        if self.tax_icms_inter_id: res.append(self.tax_icms_inter_id.id)
        if self.tax_icms_intra_id: res.append(self.tax_icms_intra_id.id)
        if self.tax_icms_fcp_id: res.append(self.tax_icms_fcp_id.id)
        if self.tax_ipi_id: res.append(self.tax_ipi_id.id)
        if self.tax_pis_id: res.append(self.tax_pis_id.id)
        if self.tax_cofins_id: res.append(self.tax_cofins_id.id)
        if self.tax_issqn_id: res.append(self.tax_issqn_id.id)
        if self.tax_ii_id: res.append(self.tax_ii_id.id)
        if self.tax_csll_id: res.append(self.tax_csll_id.id)
        if self.tax_irrf_id: res.append(self.tax_irrf_id.id)
        if self.tax_inss_id: res.append(self.tax_inss_id.id)
        if self.tax_outros_id: res.append(self.tax_outros_id.id)
        return res
            

    @api.model
    def create(self, vals):
        if vals.get('tax_icms_id',False):
            tax = self.env['account.tax'].search([('id','=',vals['tax_icms_id'])])
            vals['icms_aliquota'] = tax.amount
        res = super(AccountInvoiceLine, self).create(vals)
        res. _update_invoice_line_ids()
        return res

    @api.multi
    def write(self, vals):
        for line in self:
            if line.tax_icms_id:
                vals['icms_aliquota'] = line.tax_icms_id.amount
        result = super(AccountInvoiceLine, self).write(vals)
        return result
