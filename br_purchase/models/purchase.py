import datetime

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp

READONLY_STATES = {
    'purchase': [('readonly', True)],
    'done': [('readonly', True)],
    'cancel': [('readonly', True)],
}

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.price_total')
    def _amount_all(self):
        super(PurchaseOrder, self)._amount_all()
        for order in self:
            price_total = sum(l.price_total for l in order.order_line)
            price_subtotal = sum(l.price_subtotal for l in order.order_line)
            order.update({
                'amount_untaxed': price_subtotal,
                'amount_tax': price_total - price_subtotal,
                'amount_total': price_total,
                'total_tax': price_total - price_subtotal,
                'total_desconto': sum(l.valor_desconto
                                      for l in order.order_line),
                'total_bruto': sum(l.valor_bruto
                                   for l in order.order_line),
            })

    def _get_deadline_order(self):
        params = self.env['ir.config_parameter'].sudo()
        days = int(params.get_param('purchase.days_lock_deadline', default=7))
        return fields.date.today()+datetime.timedelta(days)

    deadline_order = fields.Date('Data Final Cotação', states=READONLY_STATES, index=True, copy=False, default=_get_deadline_order, required=True)
    tipo_frete = fields.Selection([('0', '0 - Contratação do Frete por conta do Remetente (CIF)'),
         ('1', '1 - Contratação do Frete por conta do Destinatário (FOB)'),
         ('2', '2 - Contratação do Frete por conta de Terceiros'),
         ('3', '3 - Transporte Próprio por conta do Remetente'),
         ('4', '4 - Transporte Próprio por conta do Destinatário'),
         ('9', '9 - Sem Ocorrência de Transporte')], string="Frete", required=True, default='1', states=READONLY_STATES)
    transportadora_id = fields.Many2one('res.partner',string="Transportador",states=READONLY_STATES)
    prazo_entrega = fields.Integer(string="Prazo Entrega", default=0,states=READONLY_STATES)
    vol_especie = fields.Char(string="Espécie Volumes",states=READONLY_STATES)
    volumes_total = fields.Integer(string="Volumes", default=0,states=READONLY_STATES)
    peso_liquido = fields.Float(string="Peso Liquido", default=0.0, digits=(12,3),states=READONLY_STATES)

    total_bruto = fields.Float(
        string='Total Bruto ( = )', readonly=True, compute='_amount_all',
        digits=dp.get_precision('Account'), store=True)
    total_tax = fields.Float(
        string='Impostos ( + )', readonly=True, compute='_amount_all',
        digits=dp.get_precision('Account'), store=True)
    total_desconto = fields.Float(
        string='Desconto Total ( - )', readonly=True, compute='_amount_all',
        digits=dp.get_precision('Account'), store=True,
        help="The discount amount.")

    account_analytic_id = fields.Many2one('account.analytic.account', 'Centro Custo', copy=True, states=READONLY_STATES)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Rótulos Custo', copy=True, states=READONLY_STATES)
    name = fields.Char('Order Reference', required=True, index=True, copy=False, default='New', states=READONLY_STATES)
    origin = fields.Char('Source Document', copy=False, states=READONLY_STATES)
    partner_ref = fields.Char('Vendor Reference', copy=False, states=READONLY_STATES)

    @api.onchange('fiscal_position_id')
    def _compute_tax_id(self):
        """
        Trigger the recompute of the taxes if the fiscal position is changed
        """
        for order in self:
            order.order_line._compute_tax_id()

    @api.multi
    def print_ordem(self):
        return self.env.ref('purchase.action_report_purchase_order').report_action(self)

    @api.onchange('partner_id')
    def onchange_partner_fpos(self):
        if not self.fiscal_position_id and self.partner_id:
            fpos = self.partner_id.property_purchase_fiscal_position_id.id
            if not bool(fpos):
                fpos = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id, delivery_id=None, type_inv='in_invoice')
            self.fiscal_position_id = fpos

    @api.onchange('account_analytic_id')
    def _onchange_account_analytic_id(self):
        for order in self:
            tagsin = []
            if order.account_analytic_id:
                for tag in order.account_analytic_id.tag_ids:
                    tagsin.append(tag.id)
            order.analytic_tag_ids = [(6,0,tagsin)]
            for line in order.order_line:
                line.account_analytic_id = order.account_analytic_id
                line.analytic_tag_ids = [(6,0,tagsin)]

    @api.onchange('analytic_tag_ids')
    def _onchange_analytic_tag_ids(self):
        for order in self:
            tagsin = []
            for tag in order.analytic_tag_ids:
                tagsin.append(tag.id)
            for line in order.order_line: 
                line.analytic_tag_ids = [(6,0,tagsin)]


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_tax_context(self):
        return {
            'incluir_ipi_base': self.incluir_ipi_base,
            'icms_st_aliquota_mva': self.icms_st_aliquota_mva,
            'aliquota_icms_proprio': self.aliquota_icms_proprio,
            'icms_aliquota_reducao_base': self.icms_aliquota_reducao_base,
            'icms_st_aliquota_reducao_base':
            self.icms_st_aliquota_reducao_base,
            'ipi_reducao_bc': self.ipi_reducao_bc,
            'icms_st_aliquota_deducao': self.icms_st_aliquota_deducao,
            'fiscal_type': self.fiscal_position_type,
        }

    @api.depends('taxes_id', 'product_qty', 'price_unit', 'discount',
                 'icms_aliquota_reducao_base', 'icms_st_aliquota_reducao_base',
                 'ipi_reducao_bc', 'icms_st_aliquota_deducao',
                 'incluir_ipi_base', 'icms_st_aliquota_mva')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            ctx = line._prepare_tax_context()
            tax_ids = line.taxes_id.with_context(**ctx)
            taxes = tax_ids.compute_all(
                price, line.order_id.currency_id,
                line.product_qty, product=line.product_id,
                partner=line.order_id.partner_id)

            valor_bruto = line.price_unit * line.product_qty
            desconto = valor_bruto * line.discount / 100.0
            desconto = line.order_id.currency_id.round(desconto)

            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'valor_bruto': valor_bruto,
                'valor_desconto': desconto,
                'valor_liquido': valor_bruto - desconto,
            })

    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    fiscal_position_type = fields.Selection(
        [('saida', 'Saída'), ('entrada', 'Entrada'),
         ('import', 'Entrada Importação')],
        string="Tipo da posição fiscal")
    cfop_id = fields.Many2one('br_account.cfop', string="CFOP")

    icms_cst_normal = fields.Char(string="CST ICMS", size=5)
    icms_csosn_simples = fields.Char(string="CSOSN ICMS", size=5)
    icms_benef = fields.Many2one('br_account.beneficio.fiscal', string="Benificio Fiscal")
    icms_st_aliquota_mva = fields.Float(string='Alíquota MVA (%)',
                                        digits=dp.get_precision('Account'))
    aliquota_icms_proprio = fields.Float(
        string='Alíquota ICMS Próprio (%)',
        digits=dp.get_precision('Account'))
    incluir_ipi_base = fields.Boolean(string="Incluir IPI na Base ICMS")
    icms_aliquota_reducao_base = fields.Float(
        string='Redução Base ICMS (%)', digits=dp.get_precision('Account'))
    icms_st_aliquota_reducao_base = fields.Float(
        string='Redução Base ICMS ST(%)', digits=dp.get_precision('Account'))
    icms_st_aliquota_deducao = fields.Float(
        string="% Dedução", help="Alíquota interna ou interestadual aplicada \
         sobre o valor da operação para deduzir do ICMS ST - Para empresas \
         do Simples Nacional", digits=dp.get_precision('Account'))
    tem_difal = fields.Boolean(string="Possui Difal")

    ipi_cst = fields.Char(string='CST IPI', size=5)
    ipi_reducao_bc = fields.Float(
        string='Redução Base IPI (%)', digits=dp.get_precision('Account'))

    pis_cst = fields.Char(string='CST PIS', size=5)
    cofins_cst = fields.Char(string='CST COFINS', size=5)
    l10n_br_issqn_deduction = fields.Float(string="% Dedução de base ISSQN")

    discount = fields.Float(
        string='Discount (%)',
        digits=dp.get_precision('Discount'),
        default=0.0)

    valor_desconto = fields.Float(
        compute='_compute_amount', string='Desconto (-)', store=True,
        digits=dp.get_precision('Sale Price'))
    valor_bruto = fields.Float(
        compute='_compute_amount', string='Vlr. Bruto', store=True,
        digits=dp.get_precision('Sale Price'))
    valor_liquido  = fields.Float(
        compute='_compute_amount', string='Vlr. Bruto', store=False,
        digits=dp.get_precision('Sale Price'))

    # Dados para pivot
    date_order = fields.Datetime(related='order_id.date_order', string='Order Date', readonly=True, store=True)
    categ_id = fields.Many2one('product.category', 'Categoria',related='product_id.categ_id', readonly=True, store=True)

    
    def _update_tax_from_ncm(self):
        if self.product_id:
            ncm = self.product_id.fiscal_classification_id
            taxes = ncm.tax_icms_st_id | ncm.tax_ipi_id
            self.update({
                'icms_st_aliquota_mva': ncm.icms_st_aliquota_mva,
                'icms_st_aliquota_reducao_base':
                ncm.icms_st_aliquota_reducao_base,
                'ipi_cst': ncm.ipi_cst,
                'ipi_reducao_bc': ncm.ipi_reducao_bc,
                'taxes_id': [(6, None, [x.id for x in taxes if x])]
            })

    def _onchange_quantity(self):
        res = super(PurchaseOrderLine, self)._onchange_quantity()
        self._compute_tax_id()
        return res

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            line._update_tax_from_ncm()
            fpos = line.order_id.fiscal_position_id or \
                line.order_id.partner_id.property_account_position_id
            if fpos:
                vals = fpos.map_tax_extra_values(
                    line.product_id, line.order_id.partner_id, False, False, False, line.account_analytic_id)

                for key, value in vals.items():
                    if value and key in line._fields:
                        line.update({key: value})

                empty = line.env['account.tax'].browse()
                ipi = line.taxes_id.filtered(lambda x: x.domain == 'ipi')
                icmsst = line.taxes_id.filtered(lambda x: x.domain == 'icmsst')
                tax_ids = vals.get('tax_icms_id', empty) | \
                    vals.get('tax_icms_st_id', icmsst) | \
                    vals.get('tax_icms_inter_id', empty) | \
                    vals.get('tax_icms_intra_id', empty) | \
                    vals.get('tax_icms_fcp_id', empty) | \
                    vals.get('tax_ipi_id', ipi) | \
                    vals.get('tax_pis_id', empty) | \
                    vals.get('tax_cofins_id', empty) | \
                    vals.get('tax_ii_id', empty) | \
                    vals.get('tax_issqn_id', empty) | \
                    vals.get('tax_csll_id', empty) | \
                    vals.get('tax_irrf_id', empty) | \
                    vals.get('tax_inss_id', empty)

                line.update({
                    'taxes_id': [(6, None, [x.id for x in tax_ids if x])],
                    'fiscal_position_type': fpos.fiscal_type,
                })

    # Calcula o custo da mercadoria comprada
    @api.multi
    def _get_stock_move_price_unit(self):
        price = self.price_unit
        order = self.order_id
        ctx = self._prepare_tax_context()
        tax_ids = self.taxes_id.with_context(**ctx)
        taxes = tax_ids.compute_all(
            price,
            currency=self.order_id.currency_id,
            quantity=1.0,
            product=self.product_id,
            partner=self.order_id.partner_id)

        price = taxes['total_included']
        for tax in taxes['taxes']:
            # Quando o imposto não tem conta contábil, deduzimos que ele não é
            # recuperável e portanto somamos ao custo, como partimos do valor
            # já com imposto se existir conta diminuimos o valor deste imposto
            if tax['account_id']:
                price -= tax['amount']

        if self.product_uom.id != self.product_id.uom_id.id:
            price *= self.product_uom.factor / self.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            price = order.currency_id.compute(price,
                                              order.company_id.currency_id,
                                              round=False)
        return price

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
            idsx = [(6,0,self.order_id.analytic_tag_ids.ids)]
            self.analytic_tag_ids = idsx
            self.account_analytic_id = self.order_id.account_analytic_id
        return res


    @api.onchange('account_analytic_id')
    def onchange_analytic_id(self):
        if self.account_analytic_id != self.order_id.account_analytic_id:
            self.analytic_tag_ids = [(6,0,self.account_analytic_id.tag_ids)]
