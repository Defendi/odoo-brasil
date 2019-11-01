# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare

EDITONLY_STATES = {
    'draft': [('readonly', False)]
}

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.price_total')
    def _amount_all(self):
        super(SaleOrder, self)._amount_all()
        for order in self:
            order.update({
                'amount_total': order.total_bruto + 
                                order.total_tax +
                                order.total_frete + 
                                order.total_seguro +
                                order.total_despesas - 
                                order.total_desconto_vl,
            })

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
        line.update({
            'valor_seguro': seguro,
            'valor_frete': frete,
            'outras_despesas': despesas,
        })
        return frete, seguro, despesas

    total_despesas = fields.Float(compute='_get_despesa', 
                                  inverse='_set_despesa',
                                  string='Despesas ( + )', default=0.00,
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

    #transporte
    shipping_supplier_id = fields.Many2one('res.partner', 'Transportadora', readonly=True, states=EDITONLY_STATES, oldname='transp_id')
    freight_responsibility = fields.Selection([('0', '0 - Contratação do Frete por conta do Remetente (CIF)'),
         ('1', '1 - Contratação do Frete por conta do Destinatário (FOB)'),
         ('2', '2 - Contratação do Frete por conta de Terceiros'),
         ('3', '3 - Transporte Próprio por conta do Remetente'),
         ('4', '4 - Transporte Próprio por conta do Destinatário'),
         ('9', '9 - Sem Ocorrência de Transporte')], string="Frete", required=True, default='1', readonly=True, states=EDITONLY_STATES)
    freight_estimated = fields.Float(string="Vl Frete Estimado", readonly=True, states=EDITONLY_STATES, oldname='frete_estimado')
    delivery_time = fields.Integer(string="Prazo Entrega", default=0, readonly=True, states=EDITONLY_STATES, oldname='prazo_entrega')
    vol_especie = fields.Char(string="Espécie Volume",readonly=True, states=EDITONLY_STATES)
    volumes_total = fields.Integer(string="Nº Volumes", default=0,readonly=True, states=EDITONLY_STATES)
    peso_bruto = fields.Float(string="Peso Bruto (Kg)", default=0.0, digits=(12,3), readonly=True, states=EDITONLY_STATES)
    peso_liquido = fields.Float(string="Peso Liquido (Kg)", default=0.0, digits=(12,3), readonly=True, states=EDITONLY_STATES)

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
                    vlBruto = float("%.2f" % (l.product_uom_qty * l.price_unit))
                    percentual = self._calc_ratio(vlBruto, amount)
                    if x >= len(record.order_line):
                        vl = vlDespesas - somaItem
                    else:
                        vl = float("%.2f" % (vlDespesas * percentual))
                        somaItem += vl
                    l.update({
                        'outras_despesas': vl,
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
                    vlBruto = float("%.2f" % (l.product_uom_qty * l.price_unit))
                    percentual = self._calc_ratio(vlBruto, amount)
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
                    vlBruto = float("%.2f" % (l.product_uom_qty * l.price_unit))
                    percentual = self._calc_ratio(vlBruto, amount)
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
                    vlBruto = float("%.2f" % (l.product_uom_qty * l.price_unit))
                    percentual = self._calc_ratio(vlBruto, amount)
                    if x >= len(record.order_line):
                        vl = vlDesconto - somaItem
                    else:
                        vl = float("%.2f" % (vlDesconto * percentual))
                        somaItem += vl
                    l.update({
                        'valor_desconto': vl,
                    })
                    x += 1

    @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res['shipping_supplier_id'] = self.shipping_supplier_id.id
        res['freight_responsibility'] = self.freight_responsibility
        #res['goods_delivery_date'] = self. 
        res['weight'] = self.peso_bruto
        res['weight_net'] = self.peso_liquido
        res['kind_of_packages'] = self.vol_especie
        res['number_of_packages'] = self.volumes_total
        return res

    @api.multi
    def action_confirm(self):
        for order in self:
            if not bool(self.fiscal_position_id):
                raise UserError(
                    _("A venda precisa ter uma posição fiscal. \
                      Informe no campo Posição Fiscal qual é a \
                      forma dessa venda."))
                 
            prec = order.currency_id.decimal_places
            itens = order.order_line
            frete = round(sum(x.valor_frete for x in itens), prec)
            if frete != order.total_frete:
                raise UserError(
                    _("A soma do frete dos itens não confere com o\
                      valor total do frete. Insira novamente o valor\
                      total do frete para que o mesmo seja rateado\
                      entre os itens."))

            despesas = round(sum(x.outras_despesas for x in itens), prec)
            if despesas != order.total_despesas:
                raise UserError(
                    _("A soma de outras despesas dos itens não\
                       confere com o valor total de outras despesas.\
                       Insira novamente o valor total de outras\
                       despesas para que o mesmo seja rateado entre\
                       os itens."))

            seguro = round(sum(x.valor_seguro for x in itens), prec)
            if seguro != order.total_seguro:
                raise UserError(
                    _("A soma do seguro dos itens não confere com o\
                       valor total do seguro. Insira novamente o\
                       valor total do seguro para que o mesmo seja\
                       rateado entre os itens."))

        return super(SaleOrder, self).action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_tax_context(self):
        res = super(SaleOrderLine, self)._prepare_tax_context()
        res.update({
            'valor_frete': self.valor_frete,
            'valor_seguro': self.valor_seguro,
            'outras_despesas': self.outras_despesas,
        })
        return res

    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        vals = super(SaleOrderLine, self)._prepare_order_line_procurement(
            group_id=group_id)
        confirm = fields.Date.from_string(self.order_id.confirmation_date)
        date_planned = confirm + timedelta(days=self.customer_lead or 0.0)
        date_planned -= timedelta(days=self.order_id.company_id.security_lead)
        vals["date_planned"] = date_planned
        return vals

    valor_seguro = fields.Float(
        'Seguro', default=0.0, digits=dp.get_precision('Account'))
    outras_despesas = fields.Float(
        'Despesas', default=0.0, digits=dp.get_precision('Account'))
    valor_frete = fields.Float(
        'Frete', default=0.0, digits=dp.get_precision('Account'))

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)

        res['valor_seguro'] = self.valor_seguro
        res['outras_despesas'] = self.outras_despesas
        res['valor_frete'] = self.valor_frete
        return res
