from odoo import api, fields, models
from odoo.addons import decimal_precision as dp

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    fiscal_position_type = fields.Selection(
        related='fiscal_position_id.fiscal_type', readonly=True)
    picking_origin_id = fields.Many2one(
        'stock.picking', string="Picking Origin")

    @api.one
    @api.depends('invoice_line_ids.price_subtotal',
                 'invoice_line_ids.price_total',
                 'invoice_line_ids.weight',
                 'tax_line_ids.amount',
                 'currency_id', 'company_id')
    def _compute_amount(self):
        super(AccountInvoice, self)._compute_amount()
        lines = self.invoice_line_ids

        self.total_seguro = sum(l.valor_seguro for l in lines)
        self.total_frete = sum(l.valor_frete for l in lines)
        self.total_despesas = sum(l.outras_despesas for l in lines)
        self.amount_total = self.total_bruto - self.total_desconto + \
            self.total_tax + self.total_frete + self.total_seguro + \
            self.total_despesas
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = self.amount_total * sign
        self.amount_total_signed = self.amount_total * sign
        self.weight = sum(l.weight for l in lines)
        self.weight_net = sum(l.weight for l in lines)

    total_seguro = fields.Float(
        string='Seguro ( + )', digits=dp.get_precision('Account'),
        compute="_compute_amount")
    total_despesas = fields.Float(
        string='Despesas ( + )', digits=dp.get_precision('Account'),
        compute="_compute_amount")
    total_frete = fields.Float(
        string='Frete ( + )', digits=dp.get_precision('Account'),
        compute="_compute_amount")

    # Transporte
    goods_delivery_date = fields.Datetime(
        string="Data Entrega", help="Data para saída/entrada das mercadorias",readonly=True, states={'draft': [('readonly', False)]})
    freight_responsibility = fields.Selection(
        [('0', '0 - Contratação do Frete por conta do Remetente (CIF)'),
         ('1', '1 - Contratação do Frete por conta do Destinatário (FOB)'),
         ('2', '2 - Contratação do Frete por conta de Terceiros'),
         ('3', '3 - Transporte Próprio por conta do Remetente'),
         ('4', '4 - Transporte Próprio por conta do Destinatário'),
         ('9', '9 - Sem Ocorrência de Transporte')],
        'Modalidade do frete', default="9",readonly=True, states={'draft': [('readonly', False)]})
    shipping_supplier_id = fields.Many2one('res.partner', 'Transportadora',readonly=True, states={'draft': [('readonly', False)]})
    vehicle_plate = fields.Char('Placa do Veículo', size=7,readonly=True, states={'draft': [('readonly', False)]})
    vehicle_state_id = fields.Many2one('res.country.state', 'UF da Placa',readonly=True, states={'draft': [('readonly', False)]})
    vehicle_rntc = fields.Char('RNTC', size=20,readonly=True, states={'draft': [('readonly', False)]})

    tow_plate = fields.Char('Placa do Reboque', size=7, readonly=True, states={'draft': [('readonly', False)]})
    tow_state_id = fields.Many2one(
        'res.country.state', 'UF da Placa do Reboque',readonly=True, states={'draft': [('readonly', False)]})
    tow_rntc = fields.Char('RNTC Reboque', size=20,readonly=True, states={'draft': [('readonly', False)]})

    weight = fields.Float(string='Peso Bruto', help="O peso bruto em Kg.", digits=(12,3),readonly=True, states={'draft': [('readonly', False)]})
    weight_net = fields.Float('Peso Líquido', help="O peso líquido em Kg.", digits=(12,3),readonly=True, states={'draft': [('readonly', False)]})
    number_of_packages = fields.Integer('Nº Volumes',readonly=True, states={'draft': [('readonly', False)]})
    kind_of_packages = fields.Char('Espécie', size=60,readonly=True, states={'draft': [('readonly', False)]})
    brand_of_packages = fields.Char('Marca', size=60,readonly=True, states={'draft': [('readonly', False)]})
    notation_of_packages = fields.Char('Numeração', size=60,readonly=True, states={'draft': [('readonly', False)]})

    # Exportação
    uf_saida_pais_id = fields.Many2one(
        'res.country.state', domain=[('country_id.code', '=', 'BR')],
        string="UF Saída do País",readonly=True, states={'draft': [('readonly', False)]})
    local_embarque = fields.Char('Local de Embarque', size=60,readonly=True, states={'draft': [('readonly', False)]})
    local_despacho = fields.Char('Local de Despacho', size=60,readonly=True, states={'draft': [('readonly', False)]})

    def _prepare_edoc_vals(self, inv, inv_lines, serie_id):
        res = super(AccountInvoice, self)._prepare_edoc_vals(
            inv, inv_lines, serie_id)

        res['volume_ids'] = [(0, None, {
            'peso_bruto': inv.weight,
            'peso_liquido': inv.weight_net,
            'quantidade_volumes': inv.number_of_packages,
            'especie': inv.kind_of_packages,
            'marca': inv.brand_of_packages,
            'numeracao': inv.notation_of_packages,
        })]

        res['valor_frete'] = inv.total_frete
        res['valor_despesas'] = inv.total_despesas
        res['valor_seguro'] = inv.total_seguro
        res['modalidade_frete'] = inv.freight_responsibility
        res['transportadora_id'] = inv.shipping_supplier_id.id
        res['placa_veiculo'] = (inv.vehicle_plate or '').upper()
        res['uf_veiculo'] = inv.vehicle_state_id.code
        res['rntc'] = inv.vehicle_rntc

        res['reboque_ids'] = [(0, None, {
            'uf_veiculo': inv.tow_state_id.code,
            'rntc': inv.tow_rntc,
            'placa_veiculo': (inv.tow_plate or '').upper(),
        })]


        res['uf_saida_pais_id'] = inv.uf_saida_pais_id.id
        res['local_embarque'] = inv.local_embarque
        res['local_despacho'] = inv.local_despacho

        return res

    def _prepare_edoc_item_vals(self, invoice_line):
        vals = super(AccountInvoice, self).\
            _prepare_edoc_item_vals(invoice_line)
        vals['frete'] = invoice_line.valor_frete
        vals['seguro'] = invoice_line.valor_seguro
        vals['outras_despesas'] = invoice_line.outras_despesas
        return vals

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        super(AccountInvoice,self)._onchange_partner_id()
        if bool(self.partner_id) and bool(self.partner_id.freight_responsibility):
            self.freight_responsibility = self.partner_id.freight_responsibility
        else:
            self.freight_responsibility = '9'
        
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    valor_frete = fields.Float('(+) Frete', digits=dp.get_precision('Account'), default=0.00)
    valor_seguro = fields.Float('(+) Seguro', digits=dp.get_precision('Account'), default=0.00)
    outras_despesas = fields.Float('(+) Despesas', digits=dp.get_precision('Account'), default=0.00)

    @api.onchange('product_id','quantity')
    def _br_stock_account_onchange_product_id(self):
        if len(self.product_id) > 0:
            if self.product_id.fiscal_type == 'product':
                self.weight = self.product_id.weight * self.quantity
#             volume = self.env['prduct.packaging'].search([('product_id','=',self.product_id.id),('name','ilike','volume')],limit=1)
#             if len(volume) > 0:
                
    def _prepare_tax_context(self):
        res = super(AccountInvoiceLine, self)._prepare_tax_context()
        res.update({
            'valor_frete': self.valor_frete,
            'valor_seguro': self.valor_seguro,
            'outras_despesas': self.outras_despesas,
            'ii_despesas': self.ii_valor_despesas,
        })
        return res

    @api.one
    @api.depends('valor_frete', 'valor_seguro', 'outras_despesas')
    def _compute_price(self):
        super(AccountInvoiceLine, self)._compute_price()
        total = self.valor_bruto - self.valor_desconto + self.valor_frete + \
            self.valor_seguro + self.outras_despesas
        self.update({'price_total': total})

