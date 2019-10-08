import time

from odoo import api, fields, models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.multi
    def _get_worked_days(self):  # TODO Fazer validação se este número de
                                # dias está certo
        for item in self:
            item.workeddays = 22

    @api.multi
    def _check_date(self):
        for item in self:
            comp_date_from = time.strftime('%Y-04-01')
            comp_date_to = time.strftime('%Y-02-28')
            obj_payslip = self.env['hr.payslip']
            payslip_ids = obj_payslip.search(
                [('contract_id', '=', item.id),
                 ('date_from', '<', comp_date_from),
                 ('date_to', '>', comp_date_to)])
            if payslip_ids:
                item.calc_date = True
            else:
                item.calc_date = False

    value_va = fields.Float('Vale Alimentação', help='Valor diário')
    percent_va = fields.Float('% Vale Alimentação',
                              help='Percentagem descontada ao final do mês')
    value_vr = fields.Float('Vale Refeição', help='Valor diário')
    percent_vr = fields.Float("% Vale Refeição",
                              help='Percentual descontado ao fim do mês')
    workeddays = fields.Float(compute=_get_worked_days,
                              string="Dias trabalhados")
    transportation_voucher = fields.Float(
        'Vale Transporte', help='Valor diário')
    percent_transportation = fields.Float(
        '% Vale Transporte',
        help='Percentual descontado ao fim do mês')
    health_insurance = fields.Float(
        'Plano de saúde', help='Valor mensal do plano de saúde')
    health_insurance_dependent = fields.Float(
        'Plano de Saúde de Dependentes',
        help='Plano de Saúde para Cônjugue e Dependentes')
    calc_date = fields.Boolean(compute=_check_date, string="Calcular data")
    ir_value = fields.Float(string="Valor IR")
