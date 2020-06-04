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
    
    workeddays = fields.Float(compute=_get_worked_days, string="Dias trabalhados")

    # Vale Transporte
    transportation_voucher_has = fields.Boolean("Vale Transporte")
    transportation_voucher = fields.Float('Valor Transporte', help='Valor diário', digits=(12,2), default=0.00)
    transportation_diary_qtd = fields.Integer("Qtde diária")
    percent_transportation = fields.Float('% Vale Transporte',help='Percentual descontado ao fim do mês')
    # Vale Alimentação
    va_has = fields.Boolean("Tem vale alimentação")
    value_va = fields.Float('V.A. Valor/dia', help='Valor diário', digits=(12,2), default=0.00)
    percent_va = fields.Float('% Vale Alimentação',help='Percentagem descontada ao final do mês')
    # Vale Refeição
    vr_has = fields.Boolean("Tem vale refeição")
    value_vr = fields.Float(string="V.R. Valor/dia ",digits=(12,2), default=0.00)
    percent_vr = fields.Float(u"% Vale Refeição", help=u'Percentual descontado ao fim do mês')
    # Plano de saúde
    health_insurance_has = fields.Boolean("Tem plano saúde") 
    health_company_id = fields.Many2one('res.partner', 'Empresa/Cooperativa')
    health_insurance = fields.Float('Plano de saúde', help=u'Valor mensal do plano de saúde')
    health_insurance_dependent = fields.Float('Plano de Saúde de Dependentes', help=u'Plano de Saúde para Cônjugue e Dependentes')
    # Plano odontológico
    dental_plan_has = fields.Boolean("Tem plano dental") 
    dental_plan_company_id = fields.Many2one('res.partner', 'Empresa/Cooperativa')
    dental_plan = fields.Float('Plano de saúde', help='Valor mensal do plano dental')
    dental_plan_dependent = fields.Float('Plano Dental de Dependentes', help='Plano de Saúde para Cônjugue e Dependentes')
    # Seguro de Vida
    life_insurance_has = fields.Boolean("Tem seguro vida")
    life_company_id = fields.Many2one('res.partner', 'Seguradora')
    policy_number = fields.Char('Nr Apólice',size=50)
    
    calc_date = fields.Boolean(compute=_check_date, string="Calcular data")
    ir_value = fields.Float(string="Valor IR")
