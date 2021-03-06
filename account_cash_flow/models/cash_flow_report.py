import datetime
from datetime import date
import openerp.addons.decimal_precision as dp
from openerp import api, fields, models
from odoo.tools import float_is_zero

class CashFlowReport(models.TransientModel):
    _name = 'account.cash.flow'
    _description = 'Cash Flow Report'

    def _compute_final_amount(self):
        for item in self:
            balance = 0
            start_balance = 0
            receivables = 0
            payables = 0
            balance_period = 0
            for line in item.line_ids:
                if line.line_type != 'amount':
                    balance += line.amount
                    if line.liquidity:
                        start_balance += line.amount
                    if line.line_type == 'receivable':
                        receivables += line.amount
                    if line.line_type == 'payable':
                        payables += line.amount
                    if not line.liquidity:
                        balance_period += line.amount
            if not item.simulated:
                balance += item.start_amount

            item.start_balance = start_balance
            item.total_payables = payables
            item.total_receivables = receivables
            item.period_balance = balance_period
            item.final_amount = balance

    ignore_outstanding = fields.Boolean(string="Ignorar Vencidos?")
    account_ids = fields.Many2many('account.account', string="Filtrar Contas")
    simulated = fields.Boolean(string="Simulado?", default=False)
    start_date = fields.Date(string="Start Date", default=False)
    end_date = fields.Date(
        string="End Date", required=True,
        default=fields.date.today()+datetime.timedelta(6*365/12))
    start_amount = fields.Float(string="Initial Value",
                                digits=dp.get_precision('Account'))
    start_balance = fields.Float(string="Saldo Inicial",
                                 compute="_compute_final_amount",
                                 digits=dp.get_precision('Account'))
    total_receivables = fields.Float(string="Total de Recebimentos",
                                     compute="_compute_final_amount",
                                     digits=dp.get_precision('Account'))
    total_payables = fields.Float(string="Total de Despesas",
                                  compute="_compute_final_amount",
                                  digits=dp.get_precision('Account'))
    period_balance = fields.Float(string="Saldo do Período",
                                  compute="_compute_final_amount",
                                  digits=dp.get_precision('Account'))
    final_amount = fields.Float(string="Saldo Final",
                                compute="_compute_final_amount",
                                digits=dp.get_precision('Account'))
    line_ids = fields.One2many(
        "account.cash.flow.line", "cashflow_id",
        string="Cash Flow Lines")
    report_nature = fields.Selection(
        [('synthetic','Sintético'),('analytic','Analítico')],
        string='Natureza', default='synthetic')
    print_graphic = fields.Boolean(string="Gráfico")

    @api.multi
    def draw_chart(self):
        if self.print_graphic:
            import plotly.graph_objs as go
#             from plotly.offline.offline import _plot_html
            import pandas as pd
    
            diarios = []
            bancos = self.line_ids.filtered(lambda x: x.liquidity)
            for item in bancos:
                diarios.append((item.amount, item.name))
    
            movimentacoes = []
            if self.report_nature == 'analytic':
                for item in self.line_ids.filtered(lambda x: not x.liquidity and x.line_type != 'amount'):
                    movimentacoes.append((item.amount, item.date, item.line_type))
        
                diarios = pd.DataFrame(diarios, columns=['total', 'name'])
                moves = pd.DataFrame(
                    movimentacoes, columns=['total', 'date_maturity', 'type'])
                moves['total'] = moves["total"].astype(float)
                moves['date_maturity'] = pd.to_datetime(moves["date_maturity"])
                moves['receitas'] = moves["total"]
                moves['despesas'] = moves["total"]
        
                moves.ix[moves.type == 'payable', 'receitas'] = 0.0
                moves.ix[moves.type == 'receivable', 'despesas'] = 0.0
                moves = moves.sort_values(by="date_maturity")
                moves["acumulado"] = moves["total"].cumsum()
                moves["acumulado"] += diarios["total"].sum()

            else:
                for item in self.line_ids.filtered(lambda x: not x.liquidity and x.line_type == 'amount'):
                    movimentacoes.append((item.amount, item.balance, item.date))
        
                diarios = pd.DataFrame(diarios, columns=['total', 'name'])
                moves = pd.DataFrame(
                    movimentacoes, columns=['saldo', 'acumulado', 'date_maturity'])
                moves['saldo'] = moves["saldo"].astype(float)
                moves['acumulado'] = moves["acumulado"].astype(float)
                moves['date_maturity'] = pd.to_datetime(moves["date_maturity"])

                moves = moves.sort_values(by="date_maturity")

            if self.report_nature == 'analytic':
    
                saldo = []
                saldo_inicial = 0.0
        
                for index, row in diarios.iterrows():
                    saldo.append(go.Bar(
                        x=["Saldo"],
                        y=[row["total"]],
                        name=row["name"]
                    ))
                    saldo_inicial += row["total"]
        
                acumulado_x = pd.Series(["Saldo"])
                acumulado_y = pd.Series([saldo_inicial])
    
                trace3 = go.Bar(
                    x=moves['date_maturity'],
                    y=moves['receitas'],
                    name='Receitas',
                )
                trace4 = go.Bar(
                    x=moves['date_maturity'],
                    y=moves['despesas'],
                    name='Despesas',
                )
                moves.drop_duplicates(
                    subset='date_maturity', keep='last', inplace=True)
                x = acumulado_x.append(moves["date_maturity"])
                y = acumulado_y.append(moves["acumulado"])
        
                trace5 = go.Scatter(
                    x=x,
                    y=y,
                    mode='lines+markers',
                    name="Saldo",
                    line=dict(
                        shape='spline'
                    )
                )
                data = [trace3, trace4, trace5]
            else:
                trace4 = go.Bar(
                    x=moves['date_maturity'],
                    y=moves['saldo'],
                    name='Saldo Dia'
                )
                trace5 = go.Scatter(
                    x=moves["date_maturity"],
                    y=moves["acumulado"],
                    mode='lines+markers',
                    name="Acumulado",
                    line=dict(
                        shape='spline'
                    )
                )
                data = [trace4,trace5]
                
            layout = go.Layout(
                barmode='stack',
                xaxis=dict(
                    tickformat="%d-%m-%Y"
                ),
            )
            fig = go.Figure(data=data, layout=layout)
    
#             plot_html, plotdivid, width, height = _plot_html(
#                 fig, {}, True, '100%', 525, False)
            plot_html = fig.to_html()
        else:
            plot_html = '<div></div>'
        return plot_html

    @api.multi
    def calculate_liquidity(self):
        liquidity_lines = []
        if not self.simulated:
            domain = [('user_type_id.type', '=', 'liquidity')]
            if self.account_ids:
                domain += [('id', 'in', self.account_ids.ids)]
            accs = self.env['account.account'].search(domain)
            for acc in accs:
                self.env.cr.execute(
                    "select sum(debit - credit) as val from account_move_line aml \
                    inner join account_move am on aml.move_id = am.id \
                    where account_id = %s and am.state = 'posted'", (acc.id, ))
                total = self.env.cr.fetchone()
                if total[0]:
                    liquidity_lines.append({
                        'name': '%s - %s' % (acc.code, acc.name),
                        'cashflow_id': self.id,
                        'account_id': acc.id,
                        'debit': 0,
                        'credit': total[0],
                        'amount': total[0],
                        'liquidity': True,
                    })
        else:
            liquidity_lines.append({
                'name': 'Valor Inicial',
                'cashflow_id': self.id,
                'account_id': False,
                'debit': self.start_amount if self.start_amount < 0.0 else 0.0,
                'credit': self.start_amount if self.start_amount > 0.0 else 0.0,
                'amount': self.start_amount,
                'liquidity': True,
            })
            
        return liquidity_lines

    @api.multi
    def calculate_moves(self):
        moveline_obj = self.env['account.move.line']
        domain = [
            '|',
            ('account_id.user_type_id.type', '=', 'receivable'),
            ('account_id.user_type_id.type', '=', 'payable'),
            ('reconciled', '=', False),
            ('move_id.state', '!=', 'draft'),
            ('company_id', '=', self.env.user.company_id.id),
            ('date_maturity', '<=', self.end_date),
        ]
        if not self.simulated:
            if self.ignore_outstanding:
                domain += [('date_maturity', '>=', date.today())]
        elif self.start_date:
            domain += [('date_maturity', '>=', self.start_date)]
        
        moveline_ids = moveline_obj.search(domain,order='date_maturity')

        moves = []
        amount_cred = 0.0
        amount_deb = 0.0
        for move in moveline_ids:
            if self.start_date and move.date_maturity < self.start_date:
                amount_deb += move.amount_residual if move.amount_residual < 0 else 0.0 
                amount_cred += move.amount_residual if move.amount_residual > 0 else 0.0
                continue
            else:
                if amount_deb != 0.0 or amount_cred != 0.0:
                    moves.append({
                        'name': 'Saldo Anterior ***',
                        'cashflow_id': self.id,
                        'partner_id': False,
                        'journal_id': False,
                        'account_id': False,
                        'line_type': False,
                        'date': self.start_date,
                        'debit': amount_deb,
                        'credit': amount_cred,
                        'amount': amount_cred + amount_deb,
                    })
                    amount_deb = 0.0
                    amount_cred = 0.0
                    
                debit = move.amount_residual if move.amount_residual < 0 else 0.0
                credit = move.amount_residual if move.amount_residual > 0 else 0.0
                amount = credit + debit

            # Temporário: não mostra as linhas com os campos 'a receber' e
            # 'a pagar' zerados
            if not credit and not debit:
                continue

            name = "%s/%s" % (move.move_id.name, move.ref or move.name)
            moves.append({
                'name': name,
                'cashflow_id': self.id,
                'partner_id': move.partner_id.id,
                'journal_id': move.journal_id.id,
                'account_id': move.account_id.id,
                'line_type': move.account_id.internal_type,
                'date': move.date_maturity,
                'debit': debit,
                'credit': credit,
                'amount': amount,
            })
        return moves

    @api.multi
    def action_calculate_report(self):
        self.write({'line_ids': [(5, 0, 0)]})
        balance = self.start_amount if not self.simulated else 0.0
        liquidity_lines = self.calculate_liquidity()
        move_lines = self.calculate_moves()

        move_lines.sort(key=lambda x: datetime.datetime.strptime(x['date'],
                                                                 '%Y-%m-%d'))
        tot_dt = False
        tot_cr = 0.0
        tot_db = 0.0
        for lines in liquidity_lines+move_lines:
            balance_ant = balance
            balance += lines['credit'] + lines['debit']
            lines['balance'] = balance
            if not lines.get('liquidity',False):
                if not tot_dt:
                    tot_dt = lines['date']
                if tot_dt != lines['date']:
                    self.env['account.cash.flow.line'].create({
                        'name': 'Sub-Total',
                        'cashflow_id': self.id,
                        'partner_id': False,
                        'journal_id': False,
                        'account_id': False,
                        'line_type': 'amount',
                        'date': tot_dt,
                        'debit': tot_db,
                        'credit': tot_cr,
                        'amount': tot_cr-(tot_db*(-1)),
                        'balance': balance_ant,
                    })
                    tot_dt = lines['date']
                    tot_cr = lines['credit']
                    tot_db = lines['debit']
                else:
                    tot_cr += lines['credit']
                    tot_db += lines['debit']
            self.env['account.cash.flow.line'].create(lines)

        self.env['account.cash.flow.line'].create({
            'name': 'Sub-Total',
            'cashflow_id': self.id,
            'partner_id': False,
            'journal_id': False,
            'account_id': False,
            'line_type': 'amount',
            'date': tot_dt,
            'debit': tot_db,
            'credit': tot_cr,
            'amount': tot_cr-(tot_db*(-1)),
            'balance': balance,
        })


class CashFlowReportLine(models.TransientModel):
    _name = 'account.cash.flow.line'
    _description = 'Cash flow lines'

    name = fields.Char(string="Description", required=True)
    liquidity = fields.Boolean(strign="Liquidez?")
    line_type = fields.Selection(
        [('receivable', 'Recebível'), ('payable', 'Pagável'),('amount','Total')], string="Tipo")
    date = fields.Date(string="Date")
    partner_id = fields.Many2one("res.partner", string="Partner")
    account_id = fields.Many2one("account.account", string="Account")
    journal_id = fields.Many2one("account.journal", string="Journal")
    invoice_id = fields.Many2one("account.invoice", string="Invoice")
    debit = fields.Float(string="Debit",
                         digits=dp.get_precision('Account'))
    credit = fields.Float(string="Credit",
                          digits=dp.get_precision('Account'))
    amount = fields.Float(string="Balance(C-D)",
                          digits=dp.get_precision('Account'))
    balance = fields.Float(string="Accumulated Balance",
                           digits=dp.get_precision('Account'))
    cashflow_id = fields.Many2one("account.cash.flow", string="Cash Flow")
