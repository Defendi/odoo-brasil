import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('invoice_line_ids.price_subtotal',
                 'invoice_line_ids.price_total',
                 'tax_line_ids.amount',
                 'currency_id', 'company_id')
    def _compute_amount(self):
        _logger.info('>>> Calculando fatura %s...' % str(self.id))
        super(AccountInvoice, self)._compute_amount()
        lines = self.invoice_line_ids
        self.total_tax = sum(l.price_tax for l in lines)
        self.icms_base = sum(l.icms_base_calculo for l in lines)
        self.icms_value = sum(l.icms_valor for l in lines)
        self.icms_st_base = sum(l.icms_st_base_calculo for l in lines)
        self.icms_st_value = sum(l.icms_st_valor for l in lines)
        self.valor_icms_uf_remet = sum(l.icms_uf_remet for l in lines)
        self.valor_icms_uf_dest = sum(l.icms_uf_dest for l in lines)
        self.valor_icms_fcp_uf_dest = sum(l.icms_fcp_uf_dest for l in lines)
        self.valor_icms_credito = sum(l.icms_valor_credito for l in lines)
        self.issqn_base = sum(l.issqn_base_calculo for l in lines)
        self.issqn_value = sum(abs(l.issqn_valor) for l in lines)
        self.ipi_base = sum(l.ipi_base_calculo for l in lines)
        self.ipi_value = sum(l.ipi_valor for l in lines)
        self.pis_base = sum(l.pis_base_calculo for l in lines)
        self.pis_value = sum(abs(l.pis_valor) for l in lines)
        self.cofins_base = sum(l.cofins_base_calculo for l in lines)
        self.cofins_value = sum(abs(l.cofins_valor) for l in lines)
        self.ii_base = sum(l.ii_base_calculo for l in lines)
        self.ii_value = sum(l.ii_valor for l in lines)
        self.csll_base = sum(l.csll_base_calculo for l in lines)
        self.csll_value = sum(abs(l.csll_valor) for l in lines)
        self.irrf_base = sum(l.irrf_base_calculo for l in lines)
        self.irrf_value = sum(abs(l.irrf_valor) for l in lines)
        self.inss_base = sum(l.inss_base_calculo for l in lines)
        self.inss_value = sum(abs(l.inss_valor) for l in lines)
        self.outros_base = sum(l.outros_base_calculo for l in lines)
        self.outros_value = sum(abs(l.outros_valor) for l in lines)
        # FCP
        self.total_fcp = sum(l.icms_fcp for l in lines.filtered(lambda x: not x.tem_difal))
        self.total_fcp_st = sum(l.icms_fcp_st for l in lines)

        # Retenções
        self.issqn_retention = sum(
            abs(l.issqn_valor) if l.issqn_valor < 0 else 0.0 for l in lines)
        self.pis_retention = sum(
            abs(l.pis_valor) if l.pis_valor < 0 else 0.0 for l in lines)
        self.cofins_retention = sum(
            abs(l.cofins_valor) if l.cofins_valor < 0 else 0.0 for l in lines)
        self.csll_retention = sum(
            abs(l.csll_valor) if l.csll_valor < 0 else 0 for l in lines)
        self.irrf_retention = sum(
            abs(l.irrf_valor) if l.irrf_valor < 0 else 0.0 for l in lines)
        self.inss_retention = sum(
            abs(l.inss_valor) if l.inss_valor < 0 else 0.0 for l in lines)
        self.outros_retention = sum(
            abs(l.outros_valor) if l.outros_valor < 0 else 0.0 for l in lines)

        self.total_bruto = sum(l.valor_bruto for l in lines)
        self.total_desconto = sum(l.valor_desconto for l in lines)
        self.total_tributos_federais = sum(
            l.tributos_estimados_federais for l in lines)
        self.total_tributos_estaduais = sum(
            l.tributos_estimados_estaduais for l in lines)
        self.total_tributos_municipais = sum(
            l.tributos_estimados_municipais for l in lines)
        self.total_tributos_estimados = sum(
            l.tributos_estimados for l in lines)
#         self.total_despesas_aduana = sum(
#             l.ii_valor_despesas for l in lines)
        # TOTAL
#         self.amount_total = self.total_bruto - \
#             self.total_desconto + self.total_tax + self.total_despesas_aduana
        self.amount_total = self.total_bruto - \
            self.total_desconto + self.total_tax
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = self.amount_total * sign
        self.amount_total_signed = self.amount_total * sign
        self.taxa_icms_credito = (self.valor_icms_credito / (self.total_bruto - self.total_desconto)) * 100 \
                                if (self.total_bruto - self.total_desconto) > 0.0 else 0.0 

    @api.one
    @api.depends('move_id.line_ids')
    def _total_icms(self):
        lines = self.invoice_line_ids
        self.total_icms_valor_credito = sum(
            l.icms_valor_credito for l in lines)

    @api.one
    @api.depends('move_id.line_ids')
    def _compute_receivables(self):
        self.receivable_move_line_ids = self.move_id.line_ids.filtered(
            lambda m: m.account_id.user_type_id.type == 'receivable'
            ).sorted(key=lambda m: m.date_maturity)

    @api.one
    @api.depends('move_id.line_ids')
    def _compute_payables(self):
        payable_lines = self.move_id.line_ids.filtered(
            lambda m: m.account_id.user_type_id.type == 'payable'
            ).sorted(key=lambda m: m.date_maturity)
        self.payable_move_line_ids = payable_lines

    date_invoice = fields.Date(string='Invoice Date',
        readonly=True, states={'draft': [('readonly', False)]}, index=True, required=True,
        help="Keep empty to use the current date", copy=False, default=fields.Date.context_today)

    total_tax = fields.Float(
        string='Impostos ( + )', readonly=True, compute='_compute_amount',
        digits=dp.get_precision('Account'), store=True)

    receivable_move_line_ids = fields.Many2many(
        'account.move.line', string='Receivable Move Lines',
        compute='_compute_receivables')

    payable_move_line_ids = fields.Many2many(
        'account.move.line', string='Payable Move Lines',
        compute='_compute_payables')

    issuer = fields.Selection(
        [('0', 'Terceiros'), ('1', 'Emissão própria')], 'Emitente',
        default='1', readonly=True, states={'draft': [('readonly', False)]})
    
    vendor_number = fields.Char(
        'Número NF Entrada', size=18, readonly=True,
        states={'draft': [('readonly', False)]},
        help="Número da Nota Fiscal do Fornecedor", copy=False)
    
    vendor_serie = fields.Char(
        'Série NF Entrada', size=12, readonly=True,
        states={'draft': [('readonly', False)]},
        help="Série do número da Nota Fiscal do Fornecedor",copy=False)

    product_serie_id = fields.Many2one(
        'br_account.document.serie', string='Série produtos',
        domain="[('fiscal_document_id', '=', product_document_id),\
        ('company_id','=',company_id)]", readonly=True,
        states={'draft': [('readonly', False)]})

    product_document_nr = fields.Integer(
        string='Número Doc', readonly=True, 
        states={'draft': [('readonly', False)]},
        copy=False, default=0)

    product_document_id = fields.Many2one(
        'br_account.fiscal.document', string='Documento produtos',
        readonly=True, states={'draft': [('readonly', False)]})
    
    product_is_eletronic = fields.Boolean(
        related='product_document_id.electronic', type='boolean',
        store=True, string='NF/CT Eletrônico', readonly=True)

    service_serie_id = fields.Many2one(
        'br_account.document.serie', string='Série serviços',
        domain="[('fiscal_document_id', '=', service_document_id),\
        ('company_id','=',company_id)]", readonly=True,
        states={'draft': [('readonly', False)]})
    
    service_document_nr = fields.Integer(
        string='Número RPS', readonly=True, 
        states={'draft': [('readonly', False)]},
        copy=False, default=0)
    
    service_document_id = fields.Many2one(
        'br_account.fiscal.document', string='Documento serviços',
        readonly=True, states={'draft': [('readonly', False)]})

    service_is_eletronic = fields.Boolean(
        related='service_document_id.electronic', type='boolean',
        store=True, string='NFS Eletrônico', readonly=True)

    fiscal_document_related_ids = fields.One2many(
        'br_account.document.related', 'invoice_id',
        'Documento Fiscal Relacionado', readonly=True,
        states={'draft': [('readonly', False)]})
    fiscal_observation_ids = fields.Many2many(
        'br_account.fiscal.observation', string="Observações Fiscais",
        readonly=True, states={'draft': [('readonly', False)]})
    fiscal_comment = fields.Text(
        'Observação Fiscal', readonly=True,
        states={'draft': [('readonly', False)]})

    total_bruto = fields.Float(
        string='Total Bruto ( = )', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    total_desconto = fields.Float(
        string='Desconto ( - )', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')

    icms_base = fields.Float(
        string='Base ICMS', store=True, compute='_compute_amount',
        digits=dp.get_precision('Account'))
    icms_value = fields.Float(
        string='Valor ICMS', digits=dp.get_precision('Account'),
        compute='_compute_amount', store=True)
    icms_st_base = fields.Float(
        string='Base ICMS ST', store=True, compute='_compute_amount',
        digits=dp.get_precision('Account'))
    icms_st_value = fields.Float(
        string='Valor ICMS ST', store=True, compute='_compute_amount',
        digits=dp.get_precision('Account'))
    valor_icms_fcp_uf_dest = fields.Float(
        string="Total ICMS FCP", store=True, compute='_compute_amount',
        help='Total total do ICMS relativo Fundo de Combate à Pobreza (FCP) \
        da UF de destino')
    valor_icms_uf_dest = fields.Float(
        string="ICMS Destino", store=True, compute='_compute_amount',
        help='Valor total do ICMS Interestadual para a UF de destino')
    valor_icms_uf_remet = fields.Float(
        string="ICMS Remetente", store=True, compute='_compute_amount',
        help='Valor total do ICMS Interestadual para a UF do Remetente')
    valor_icms_credito = fields.Float(string="Total ICMS Crédito", 
        store=True, compute='_compute_amount', digits=dp.get_precision('Account'),
        help='Valor total do crédito de ICMS do Simples Nacional')
    taxa_icms_credito = fields.Float(string="Taxa ICMS Crédito", 
        store=True, compute='_compute_amount', digits=(12,2),
        help='Taxa total do crédito de ICMS do Simples Nacional')
    issqn_base = fields.Float(
        string='Base ISSQN', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    issqn_value = fields.Float(
        string='Valor ISSQN', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    issqn_retention = fields.Float(
        string='ISSQN Retido', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    ipi_base = fields.Float(
        string='Base IPI', store=True, digits=dp.get_precision('Account'),
        compute='_compute_amount')
    ipi_base_other = fields.Float(
        string="Base IPI Outras", store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    ipi_value = fields.Float(
        string='Valor IPI', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    pis_base = fields.Float(
        string='Base PIS', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    pis_value = fields.Float(
        string='Valor PIS', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    pis_retention = fields.Float(
        string='PIS Retido', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    cofins_base = fields.Float(
        string='Base COFINS', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    cofins_value = fields.Float(
        string='Valor COFINS', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount',
        readonly=True)
    cofins_retention = fields.Float(
        string='COFINS Retido', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount',
        readonly=True)
    ii_base = fields.Float(
        string='Base II', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    ii_value = fields.Float(
        string='Valor II', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    csll_base = fields.Float(
        string='Base CSLL', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    csll_value = fields.Float(
        string='Valor CSLL', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    csll_retention = fields.Float(
        string='CSLL Retido', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    irrf_base = fields.Float(
        string='Base IRRF', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    irrf_value = fields.Float(
        string='Valor IRRF', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    irrf_retention = fields.Float(
        string='IRRF Retido', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    inss_base = fields.Float(
        string='Base INSS', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    inss_value = fields.Float(
        string='Valor INSS', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    inss_retention = fields.Float(
        string='INSS Retido', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    outros_base = fields.Float(
        string='Base Outras Retenções', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    outros_value = fields.Float(
        string='Valor Outras Retenções', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    outros_retention = fields.Float(
        string='Outras Retido', store=True,
        digits=dp.get_precision('Account'), compute='_compute_amount')
    total_tributos_federais = fields.Float(
        string='Total de Tributos Federais',
        store=True,
        digits=dp.get_precision('Account'),
        compute='_compute_amount')
    total_tributos_estaduais = fields.Float(
        string='Total de Tributos Estaduais',
        store=True,
        digits=dp.get_precision('Account'),
        compute='_compute_amount')
    total_tributos_municipais = fields.Float(
        string='Total de Tributos Municipais',
        store=True,
        digits=dp.get_precision('Account'),
        compute='_compute_amount')
    total_tributos_estimados = fields.Float(
        string='Total de Tributos',
        store=True,
        digits=dp.get_precision('Account'),
        compute='_compute_amount')
    total_fcp = fields.Float(
        string="Total FCP", store=True, compute='_compute_amount',
        help=u'Total do Fundo de Combate à Pobreza (FCP)')
    total_fcp_st = fields.Float(
        string="Total FCP ST", store=True, compute='_compute_amount',
        help=u'Total do Fundo de Combate à Pobreza ST (FCP ST)')
    total_icms_valor_credito = fields.Float(
        string='Total de ICMS valor Crédito', compute='_total_icms',
        store=True, digits=dp.get_precision('Account'))
    total_despesas_aduana = fields.Float(
        string='Desp.Aduana ( + )', 
        digits=dp.get_precision('Account'))
    
    account_analytic_id = fields.Many2one('account.analytic.account', 'Centro Custo', old_name='account_analitic_id',
                                          copy=True, readonly=True, states={'draft': [('readonly', False)]})
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Rótulos Custo', 
                                        copy=True, readonly=True, states={'draft': [('readonly', False)]})
    
    product_id = fields.Many2one('product.product', related='invoice_line_ids.product_id', string='Produto')

    @api.multi
    @api.constrains('type', 'issuer', 'partner_id', 'vendor_serie', 'vendor_number')
    def _check_vendor_number(self):
        # Verificação se já existe a fatura cadastrada
        for inv in self:
            if inv.type == 'in_invoice' and inv.issuer == '0' and bool(inv.partner_id) and bool(inv.vendor_serie) and bool(inv.vendor_number): 
                if inv.env['account.invoice'].search([('id','!=',inv.id),
                                                      ('partner_id','=',inv.partner_id.id),
                                                      ('vendor_serie','=',inv.vendor_serie),
                                                      ('vendor_number','=',inv.vendor_number)]):
                        raise UserError('Não é possível ter mais que uma fatura com o mesmo número de um único fornecedor.')
        return True

    @api.onchange('account_analytic_id')
    def _onchange_account_analytic_id(self):
        for inv in self:
            tagsin = [(6,0,self.account_analytic_id.tag_ids.ids)]
            inv.analytic_tag_ids = tagsin
            for line in inv.invoice_line_ids:
                line.account_analytic_id = inv.account_analytic_id
                line.analytic_tag_ids = tagsin

    @api.onchange('analytic_tag_ids')
    def _onchange_analytic_tag_ids(self):
        for inv in self:
            tagsin = [(6,0,self.account_analytic_id.tag_ids.ids)]
            for line in inv.invoice_line_ids: 
                line.analytic_tag_ids = tagsin

    @api.onchange('type')
    def _onchange_type(self):
        if self.type in ('out_invoice','in_refund','out_refund'):
            self.issuer = '1'
        else:
            self.issuer = '0'

    @api.onchange('product_document_id')
    def _onchange_product_document_id(self):
        series = self.env['br_account.document.serie'].search(
            [('fiscal_document_id', '=', self.product_document_id.id),
             ('active','=', True)], limit=1, order='code')
        self.product_serie_id = series and series[0].id or False
        self.product_document_nr = 0

    @api.onchange('service_document_id')
    def _onchange_service_document_id(self):
        series = self.env['br_account.document.serie'].search(
            [('fiscal_document_id', '=', self.service_document_id.id),
             ('active','=', True)], limit=1, order='code')
        self.service_serie_id = series and series[0].id or False
        self.service_document_nr = 0

    @api.onchange('issuer')
    def _onchange_issuer(self):
        if self.issuer == '0' and self.type in ('in_invoice', 'in_refund'):
            self.fiscal_document_id = None
            self.document_serie_id = None

    def button_recalculate(self):
        for inv in self:
            inv.tax_line_ids = [(5, 0, 0)]
            if len(inv.fiscal_position_id) and (inv.fiscal_position_id.account_id):
                inv.account_id = inv.fiscal_position_id.account_id
            else:
                inv.account_id = inv.partner_id.property_account_receivable_id
            inv._onchange_br_account_fiscal_position_id()
            inv.compute_taxes()

    @api.onchange('fiscal_position_id')
    def _onchange_br_account_fiscal_position_id(self):
        if self.fiscal_position_id and self.fiscal_position_id.account_id:
            self.account_id = self.fiscal_position_id.account_id.id
        if self.fiscal_position_id and self.fiscal_position_id.journal_id:
            self.journal_id = self.fiscal_position_id.journal_id

        self.product_serie_id = self.fiscal_position_id.product_serie_id.id
        self.product_document_id = \
            self.fiscal_position_id.product_document_id.id

        self.service_serie_id = self.fiscal_position_id.service_serie_id.id
        self.service_document_id = \
            self.fiscal_position_id.service_document_id.id

        ob_ids = [x.id for x in self.fiscal_position_id.fiscal_observation_ids]
        self.fiscal_observation_ids = [(6, False, ob_ids)]
        #TODO: Fazer a alteração fiscal
        for line in self.invoice_line_ids:
            line.update(self.env['account.invoice.line']._clear_tax_id())
            line._br_account_onchange_product_id()
            line._compute_tax_id()

    @api.multi
    def action_invoice_cancel_paid(self):
        if self.filtered(lambda inv: inv.state not in ['proforma2', 'draft',
                                                       'open', 'paid']):
            raise UserError(_("Invoice must be in draft, Pro-forma or open \
                              state in order to be cancelled."))
        return self.action_cancel()

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()

        contador = 0

        for line in self.invoice_line_ids:
            if line.quantity == 0:
                continue
            res[contador]['price'] = line.price_total

            price = line.price_unit * (1 - (
                line.discount or 0.0) / 100.0)

            ctx = line._prepare_tax_context()
            tax_ids = line.invoice_line_tax_ids.with_context(**ctx)

            taxes_dict = tax_ids.compute_all(
                price, self.currency_id, line.quantity,
                product=line.product_id, partner=self.partner_id)
            
            for tax in line.invoice_line_tax_ids:
                _logger.info(str(tax.name))
                tax_dict = next(x for x in taxes_dict['taxes'] if x['id'] == tax.id)
                
                if not tax.price_include and (not tax.account_id or tax.deduced_account_id):
                    if tax_dict['amount'] > 0.0:
                        res[contador]['price'] += tax_dict['amount']
                    if tax_dict['amount'] < 0.0 and tax.deduced_account_id:
                        res[contador]['price'] += tax_dict['amount'] 
                        
                    
                if tax.price_include and (tax.account_id and not tax.deduced_account_id):
                    if tax_dict['amount'] > 0.0:  # Negativo é retido
                        res[contador]['price'] -= tax_dict['amount']

            contador += 1
        return res


    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        res = super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)
        count = 1
        for invoice_line in res:
            line = invoice_line[2]
            line['ref'] = self.origin
            if line['name'] == '/' or (
               line['name'] == self.name and self.name):
                line['name'] = "%02d" % count
                count += 1
            if not line.get('analytic_account_id',False):
                line['analytic_account_id'] = self.account_analytic_id.id
            if not line.get('analytic_tag_ids',False) or len(line['analytic_tag_ids']) == 0:
                tagsin = []
                for tag in self.analytic_tag_ids:
                    tagsin.append(tag.id)
                line['analytic_tag_ids'] = [(6,0,tagsin)]
        return res

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.invoice_line_ids:
            other_taxes = line.invoice_line_tax_ids.filtered(
                lambda x: not x.domain)

            line.invoice_line_tax_ids = line.tax_icms_id | line.tax_icms_st_id | \
                line.tax_icms_inter_id | line.tax_icms_intra_id | \
                line.tax_icms_fcp_id | line.tax_icms_fcp_st_id | line.tax_ipi_id | \
                line.tax_pis_id | line.tax_cofins_id | line.tax_issqn_id | \
                line.tax_ii_id | line.tax_csll_id | line.tax_irrf_id | \
                line.tax_inss_id | other_taxes | line.tax_outros_id

            ctx = line._prepare_tax_context()
            tax_ids = line.invoice_line_tax_ids.with_context(**ctx)

            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_ids.compute_all(
                price_unit, self.currency_id, line.quantity,
                line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(
                    tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += round(val['amount'], 2)
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped

    @api.model
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            if tax_line.amount_total and tax_line.tax_id.account_id:
                tax = tax_line.tax_id
                if tax.amount_type == "group":
                    for child_tax in tax.children_tax_ids:
                        done_taxes.append(child_tax.id)
                res.append({
                    'invoice_tax_line_id': tax_line.id,
                    'tax_line_id': tax_line.tax_id.id,
                    'type': 'tax',
                    'name': tax_line.name,
                    'price_unit': tax_line.amount_total,
                    'quantity': 1,
                    'price': tax_line.amount_total,
                    'account_id': tax_line.account_id.id,
                    'account_analytic_id': tax_line.account_analytic_id.id,
                    'invoice_id': self.id,
                    'tax_ids': [(6, 0, list(done_taxes))] if tax_line.tax_id.include_base_amount else []
                })
                done_taxes.append(tax.id)
            if tax_line.amount and tax_line.tax_id.deduced_account_id:
                tax = tax_line.tax_id
                done_taxes.append(tax.id)
                res.append({
                    'invoice_tax_line_id': tax_line.id,
                    'tax_line_id': tax_line.tax_id.id,
                    'type': 'tax',
                    'name': tax_line.name,
                    'price_unit': tax_line.amount * -1,
                    'quantity': 1,
                    'price': tax_line.amount * -1,
                    'account_id': tax_line.tax_id.deduced_account_id.id,
                    'account_analytic_id': tax_line.account_analytic_id.id,
                    'invoice_id': self.id,
                    'tax_ids': [(6, 0, done_taxes)]
                    if tax_line.tax_id.include_base_amount else []
                })
        return res

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None):
        res = super(AccountInvoice, self)._prepare_refund(
            invoice, date_invoice=date_invoice, date=date,
            description=description, journal_id=journal_id)
        docs_related = self._prepare_related_documents(invoice)
        res['fiscal_document_related_ids'] = docs_related
        res['product_document_id'] = invoice.product_document_id.id
        res['product_serie_id'] = invoice.product_serie_id.id
        res['service_document_id'] = invoice.service_document_id.id
        res['service_serie_id'] = invoice.service_serie_id.id
        return res

    def _prepare_related_documents(self, invoice):
        doc_related = self.env['br_account.document.related']
        related_vals = []
        for doc in invoice.invoice_eletronic_ids:
            vals = {'invoice_related_id': invoice.id,
                    'document_type':
                        doc_related.translate_document_type(
                            invoice.product_document_id.code),
                    'access_key': doc.chave_nfe,
                    'numero': doc.numero}
            related = (0, False, vals)
            related_vals.append(related)
        return related_vals 

    def has_inutilized(self,serie,number):
        inv_inutilized = self.env['invoice.eletronic.inutilized'].search([
            ('serie', '=', serie.id),('numeration_start','>=',number),('numeration_end','<=',number)], limit=1)
        if len(inv_inutilized) > 0:
            return True
        else:
            return False
        