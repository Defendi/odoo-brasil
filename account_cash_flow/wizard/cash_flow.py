# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime
import openerp.addons.decimal_precision as dp
from openerp import api, fields, models


class CashFlowWizard(models.TransientModel):
    _name = 'account.cash.flow.wizard'
    _description = """Assistente de Fluxo de Caixa"""

    simulated = fields.Boolean(string="Simulado?", default=False)
    start_date = fields.Date(string="Start Date", default=False, help="""Data inicial de caixa quando a liquidez é simulada pelo valor inicial.""")
    end_date = fields.Date(string="End Date", required=True, default=fields.date.today() + datetime.timedelta(6 * 365 / 12), help='Data final do demonstrativo de caixa')
    start_amount = fields.Float(string="Initial value",digits=dp.get_precision('Account'), default=0.0)
    account_ids = fields.Many2many('account.account', string="Filtrar Contas")
    print_report = fields.Boolean(string="Grade?", default=False)
    print_graphic = fields.Boolean(string="Gráfico?", default=False)
    ignore_outstanding = fields.Boolean(string="Ignorar Vencidos?", default=False)
    report_nature = fields.Selection([('synthetic','Sintético'),('analytic','Analítico')],string='Natureza', default='synthetic')
    
    def _prepare_vals(self):
        return {
            'simulated': self.simulated,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'start_amount': self.start_amount,
            'ignore_outstanding': self.ignore_outstanding,
            'report_nature': self.report_nature,
            'print_graphic': self.print_graphic,
            'account_ids': [(6, None, self.account_ids.ids)]
        }
        
        
    @api.multi
    def button_calculate(self):
        vals = self._prepare_vals()
        cashflow_id = self.env['account.cash.flow'].create(vals)
        cashflow_id.action_calculate_report()

        if not self.print_report:
            return self.env.ref('account_cash_flow\
.account_cash_flow_html_report')\
                .report_action(cashflow_id)

        dummy, action_id = self.env['ir.model.data'].get_object_reference(
            'account_cash_flow', 'account_cash_flow_report_action')
        vals = self.env['ir.actions.act_window'].browse(action_id).read()[0]
        vals['domain'] = [('cashflow_id', '=', cashflow_id.id)]
        vals['context'] = {'search_default_cashflow_id': cashflow_id.id}
        return vals
