# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.tools import float_compare


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.price_total')
    def _amount_all(self):
        super(PurchaseOrder, self)._amount_all()
        for order in self:
            order.update({
                'amount_total': order.total_bruto + 
                                order.total_tax +
                                order.total_frete + 
                                order.total_seguro +
                                order.total_despesas +
                                order.total_despesas_aduana - 
                                order.total_desconto_vl,
            })
#         self._onchange_despesas_frete_seguro()

    def _calc_ratio(self, qty, total):
        if total > 0:
            return qty / total
        else:
            return 0

    def calc_rateio(self, line, total):
        porcentagem = self._calc_ratio(line.valor_bruto, total)
        frete = self.total_frete * porcentagem
        seguro = self.total_seguro * porcentagem
        despesas = self.total_despesas * porcentagem
        aduana = self.total_despesas_aduana * porcentagem
        line.update({
            'valor_seguro': seguro,
            'valor_frete': frete,
            'outras_despesas': despesas,
            'valor_aduana': aduana
        })
        return frete, seguro, despesas, aduana

    def calc_total_amount(self):
        amount = 0
        for line in self.order_line:
            if line.product_id.fiscal_type == 'product':
                amount += line.valor_bruto
        return amount

#     @api.onchange('total_despesas', 'total_seguro',
#                   'total_frete', 'total_despesas_aduana')
#     def _onchange_despesas_frete_seguro(self):
#         for order in self:
#             amount = order.calc_total_amount()
#             sub_frete = order.total_frete
#             sub_seguro = order.total_seguro
#             sub_aduana = order.total_despesas_aduana
#             sub_desp = order.total_despesas
#             for l in order.order_line:
#                 if l.product_id.fiscal_type == 'service':
#                     continue
#                 else:
#                     frete, seguro, despesas, aduana = order.calc_rateio(
#                         l, amount)
#                     sub_frete -= round(frete, 2)
#                     sub_seguro -= round(seguro, 2)
#                     sub_aduana -= round(aduana, 2)
#                     sub_desp -= round(despesas, 2)
#             if order.order_line:
#                 order.order_line[0].update({
#                     'valor_seguro':
#                         order.order_line[0].valor_seguro + sub_seguro,
#                     'valor_frete':
#                         order.order_line[0].valor_frete + sub_frete,
#                     'outras_despesas':
#                         order.order_line[0].outras_despesas + sub_desp,
#                     'valor_aduana':
#                         order.order_line[0].valor_aduana + sub_aduana
#                     })

    total_despesas = fields.Float(compute='_get_despesa', 
                                  inverse='_set_despesa',
                                  string='Despesas ( + )', default=0.00,
                                  digits=dp.get_precision('Account'),
                                  readonly=True, store=True,
                                  states={'draft': [('readonly', False)],
                                          'sent': [('readonly', False)],
                                          'purchase': [('readonly', False)]})

    
    
    total_despesas_aduana = fields.Float(compute='_get_aduana', 
                               inverse='_set_aduana',
                               string='D.Aduana ( + )', default=0.00,
                               digits=dp.get_precision('Account'),
                               readonly=True, store=True,
                               states={'draft': [('readonly', False)],
                                       'sent': [('readonly', False)],
                                       'purchase': [('readonly', False)]})


    total_seguro = fields.Float(compute='_get_seguro', 
                               inverse='_set_seguro',
                               string='Seguro ( + )', default=0.00,
                               digits=dp.get_precision('Account'),
                               readonly=True, store=True,
                               states={'draft': [('readonly', False)],
                                       'sent': [('readonly', False)],
                                       'purchase': [('readonly', False)]})

    total_frete = fields.Float(compute='_get_frete', 
                               inverse='_set_frete',
                               string='Frete ( + )', default=0.00,
                               digits=dp.get_precision('Account'),
                               store=True, readonly=True, 
                               states={'draft': [('readonly', False)],
                                       'sent': [('readonly', False)],
                                       'purchase': [('readonly', False)]})
        
    total_desconto_vl = fields.Float(compute='_get_desconto', 
                                 inverse='_set_desconto',
                                 string='Desconto ( - )',
                                 store=True, default=0.00,
                                 digits=dp.get_precision('Account'),
                                 readonly=True,
                                 states={'draft': [('readonly', False)],
                                         'sent': [('readonly', False)],
                                         'purchase': [('readonly', False)]})

    # Total Despesa
    @api.depends('order_line.outras_despesas')
    def _get_despesa(self):
        for record in self:
            despesas = 0.0
            for line in record.order_line:
                despesas += line.outras_despesas
            record.total_despesas = despesas
    
    @api.onchange('total_despesas')
    def _set_despesa(self):
        vlDespesas = self.total_despesas
        for record in self:
            amount = 0.0
            despesas = 0.0
            for line in record.order_line:
                amount += line.valor_bruto
                despesas += line.outras_despesas
            if float_compare(vlDespesas,despesas,precision_rounding=2) != 0:
                somaItem = 0.0
                x = 1
                for l in record.order_line:
                    percentual = self._calc_ratio(l.valor_bruto, amount)
                    if x >= len(record.order_line):
                        vl = vlDespesas - somaItem
                    else:
                        vl = float("%.2f" % (vlDespesas * percentual))
                        somaItem += vl
                    l.update({
                        'outras_despesas': vl,
                    })
                    x += 1

    # Total Desp. Aduaneira
    @api.depends('order_line.valor_aduana')
    def _get_aduana(self):
        for record in self:
            despesas = 0.0
            for line in record.order_line:
                despesas += line.valor_aduana
            record.total_despesas_aduana = despesas
    
    @api.onchange('total_despesas_aduana')
    def _set_aduana(self):
        vlDespesas = self.total_despesas_aduana
        for record in self:
            amount = 0.0
            despesas = 0.0
            for line in record.order_line:
                amount += line.valor_bruto
                despesas += line.valor_aduana
            if float_compare(vlDespesas,despesas,precision_rounding=2) != 0:
                somaItem = 0.0
                x = 1
                for l in record.order_line:
                    percentual = self._calc_ratio(l.valor_bruto, amount)
                    if x >= len(record.order_line):
                        vl = vlDespesas - somaItem
                    else:
                        vl = float("%.2f" % (vlDespesas * percentual))
                        somaItem += vl
                    l.update({
                        'valor_aduana': vl,
                    })
                    x += 1

    # Total Seguro
    @api.depends('order_line.valor_seguro')
    def _get_seguro(self):
        for record in self:
            seguro = 0.0
            for line in record.order_line:
                seguro += line.valor_seguro
            record.total_seguro = seguro
    
    @api.onchange('total_seguro')
    def _set_seguro(self):
        vlSeguro = self.total_seguro
        for record in self:
            amount = 0.0
            seguro = 0.0
            for line in record.order_line:
                amount += line.valor_bruto
                seguro += line.valor_seguro
            if float_compare(vlSeguro,seguro,precision_rounding=2) != 0:
                somaItem = 0.0
                x = 1
                for l in record.order_line:
                    percentual = self._calc_ratio(l.valor_bruto, amount)
                    if x >= len(record.order_line):
                        vl = vlSeguro - somaItem
                    else:
                        vl = float("%.2f" % (vlSeguro * percentual))
                        somaItem += vl
                    l.update({
                        'valor_seguro': vl,
                    })
                    x += 1

    # Total Frete
    @api.depends('order_line.valor_frete')
    def _get_frete(self):
        for record in self:
            frete = 0.0
            for line in record.order_line:
                frete += line.valor_frete
            record.total_frete = frete
    
    @api.onchange('total_frete')
    def _set_frete(self):
        vlFrete = self.total_frete
        for record in self:
            amount = 0.0
            frete  = 0.0
            for line in record.order_line:
                amount += line.valor_bruto
                frete += line.valor_frete
            if float_compare(vlFrete,frete,precision_rounding=2) != 0:
                somaItem = 0.0
                x = 1
                for l in record.order_line:
                    percentual = self._calc_ratio(l.valor_bruto, amount)
                    if x >= len(record.order_line):
                        vl = vlFrete - somaItem
                    else:
                        vl = float("%.2f" % (vlFrete * percentual))
                        somaItem += vl
                    l.update({
                        'valor_frete': vl,
                    })
                    x += 1

    # Total do Desconto
    @api.depends('order_line.valor_desconto')
    def _get_desconto(self):
        for record in self:
            desc = 0.0
            for line in record.order_line:
                desc += line.valor_desconto
            record.total_desconto_vl = desc
     
    @api.onchange('total_desconto_vl')
    def _set_desconto(self):
        vlDesconto = self.total_desconto_vl
        self.total_desconto = vlDesconto
        for record in self:
            amount = 0.0
            desconto = 0.0
            for line in record.order_line:
                amount += line.valor_bruto
                desconto += line.valor_desconto
            if float_compare(vlDesconto,desconto,precision_rounding=2) != 0:
                somaItem = 0.0
                x = 1
                for l in record.order_line:
                    percentual = self._calc_ratio(l.valor_bruto, amount)
                    if x >= len(record.order_line):
                        vl = vlDesconto - somaItem
                    else:
                        vl = float("%.2f" % (vlDesconto * percentual))
                        somaItem += vl
                    l.update({
                        'valor_desconto': vl,
                    })
                    x += 1

class PuchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    valor_seguro = fields.Float(
        'Seguro', default=0.0, digits=dp.get_precision('Account'))
    outras_despesas = fields.Float(
        'Despesas', default=0.0, digits=dp.get_precision('Account'))
    valor_frete = fields.Float(
        'Frete', default=0.0, digits=dp.get_precision('Account'))
    valor_aduana = fields.Float(
        default=0.0, digits=dp.get_precision('Account'))
    valor_desconto = fields.Float(
        'Desconto', compute=False, default=0.0, digits=dp.get_precision('Account'))

    def _prepare_tax_context(self):
        res = super(PuchaseOrderLine, self)._prepare_tax_context()
        res.update({
            'valor_frete': self.valor_frete,
            'valor_seguro': self.valor_seguro,
            'outras_despesas': self.outras_despesas,
            'valor_desconto': self.valor_desconto,
            'ii_despesas': self.valor_aduana,
            'fiscal_type': self.fiscal_position_type,
        })
        return res

    @api.multi
    def _get_stock_move_price_unit(self):
        price = super(PuchaseOrderLine, self)._get_stock_move_price_unit()
        price = price + \
            (self.valor_frete/self.product_qty) + \
            (self.valor_seguro/self.product_qty) + \
            (self.outras_despesas/self.product_qty)
        return price

    @api.depends('taxes_id', 'product_qty', 'price_unit', 'discount',
                 'icms_aliquota_reducao_base', 'icms_st_aliquota_reducao_base',
                 'ipi_reducao_bc', 'icms_st_aliquota_deducao',
                 'incluir_ipi_base', 'icms_st_aliquota_mva')
    def _compute_amount(self):
        for line in self:
#             price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            price = line.price_unit - (line.valor_desconto or 0.0)
            ctx = line._prepare_tax_context()
            tax_ids = line.taxes_id.with_context(**ctx)
            taxes = tax_ids.compute_all(
                price, line.order_id.currency_id,
                line.product_qty, product=line.product_id,
                partner=line.order_id.partner_id)

            valor_bruto = line.price_unit * line.product_qty
#             desconto = valor_bruto * line.discount / 100.0
#             desconto = line.order_id.currency_id.round(desconto)
            desconto = line.valor_desconto
            tx_desc = (desconto / valor_bruto) * 100 if valor_bruto > 0.0 else 0.0

            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'valor_bruto': valor_bruto,
                'discount': tx_desc,
                'valor_liquido': valor_bruto - desconto,
            })
