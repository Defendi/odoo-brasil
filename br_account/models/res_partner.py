# © 2016 Danimar Ribeiro, Trustcode
# © 2017 Fillipe Ramos, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, fields


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = 'Partner'

    indicador_ie_dest = fields.Selection(
        [('1', u'1 - Contribuinte ICMS'),
         ('2', u'2 - Contribuinte isento de Inscrição no cadastro de \
                    Contribuintes do ICMS'),
         ('9', u'9 - Não Contribuinte, que pode ou não possuir Inscrição \
                    Estadual no Cadastro de Contribuintes do ICMS')],
        string="Indicador IE", help=u"Caso não preencher este campo vai usar a \
            regra:\n9 - para pessoa física\n1 - para pessoa jurídica com IE \
            cadastrada\n2 - para pessoa jurídica sem IE cadastrada ou 9 \
            caso o estado de destino for AM, BA, CE, GO, MG, MS, MT, PE, RN, SP"
    )

    freight_responsibility = fields.Selection(
        [('0', '0 - Contratação do Frete por conta do Remetente (CIF)'),
         ('1', '1 - Contratação do Frete por conta do Destinatário (FOB)'),
         ('2', '2 - Contratação do Frete por conta de Terceiros'),
         ('3', '3 - Transporte Próprio por conta do Remetente'),
         ('4', '4 - Transporte Próprio por conta do Destinatário'),
         ('9', '9 - Sem Ocorrência de Transporte')],
        'Modalidade do frete')

    @api.multi
    def _invoice_total(self):
        account_invoice_report = self.env['account.invoice.report']
        if not self.ids:
            self.total_invoiced = 0.0
            return True

        # Filter added to filter invoice total with only sales.
        # Journal with types: purchase, cash, general and bank
        # should not be included when calculating invoice total
        journal_ids = self.env['account.journal'].search([
            ('type', '=', 'sale')]).ids

        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self:
            # price_total is in the company currency
            all_partners_and_children[partner] = self.search([
                ('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

        # searching account.invoice.report via the orm is comparatively
        # expensive (generates queries "id in []" forcing
        # to build the full table).
        # In simple cases where all invoices are in the same currency
        # than the user's company access directly these elements

        # generate where clause to include multicompany rules
        where_query = account_invoice_report._where_calc([
            ('partner_id', 'in', all_partner_ids),
            ('state', 'not in', ['draft', 'cancel']),
            ('company_id', '=', self.env.user.company_id.id),
            ('type', 'in', ('out_invoice', 'out_refund')),
            ('journal_id', 'in', journal_ids)])
        account_invoice_report._apply_ir_rules(where_query, 'read')
        from_clause, where_clause, where_clause_params = where_query.get_sql()

        # price_total is in the company currency
        # pylint: disable=E8103
        query = """
                  SELECT SUM(price_total) as total, partner_id
                    FROM account_invoice_report account_invoice_report
                   WHERE %s
                   GROUP BY partner_id
                """ % where_clause
        self.env.cr.execute(query, where_clause_params)
        price_totals = self.env.cr.dictfetchall()
        for partner, child_ids in all_partners_and_children.items():
            total = 0.0
            for price in price_totals:
                if price['partner_id'] in child_ids:
                    total += price['total']
            partner.total_invoiced = total
