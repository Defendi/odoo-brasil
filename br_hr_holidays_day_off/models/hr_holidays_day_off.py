import datetime
import math

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

HORAS_POR_DIA = 8

class HrHolidaysDayoff(models.Model):
    _name = 'hr.holidays.dayoff'
    _description = 'Manage day off holidays'

    name = fields.Char(string='Feriado',required=True)
    date_from = fields.Datetime(string='De',required=True)
    date_to = fields.Datetime(string='Até',required=True)
    number_of_days = fields.Float(string='Dias')
    company_id = fields.Many2one(
        'res.company',
        string="Empresa",
        default=lambda self: self.env['res.company']._company_default_get('hr.holidays.dayoff')
    )
    status_id = fields.Many2one('hr.holidays.status', string="Tipo Feriado", required=True)
    employee_ids = fields.Many2many('hr.employee',string="Funcionários",help="Se vazio, todos os funcionários da empresa terão esse dia / período o dia de folga.")
    auto_confirm = fields.Boolean(string='Auto Confirma')

    @api.multi
    def validate(self):
        for rec in self:
            created = self.env['hr.holidays']
            if rec.employee_ids:
                employees = rec.employee_ids
            else:
                employees = self.env['hr.employee'].search([
                    ('company_id', '=', rec.company_id.id)
                ])
            for employee in employees:
                vals = rec._prepare_leave_from_imposed_day()
                vals.update({'employee_id': employee.id})
                leave = self.env['hr.holidays'].create(vals)
                leave._onchange_date_from()
                created |= leave
            if rec.auto_confirm:
                created.action_validate()

    @api.model
    def _get_duration(self):
        self.ensure_one()
        from_dt = fields.Datetime.from_string(self.date_from)
        to_dt = fields.Datetime.from_string(self.date_to)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day

    @api.multi
    def _set_duration(self):
        self.ensure_one()
        if (self.date_to and self.date_from and
                self.date_from <= self.date_to):
            diff_day = self._get_duration()
            self.number_of_days = self.compute_nb_days(diff_day)
        else:
            self.number_of_days = 0

    @api.onchange('date_from', 'date_to')
    def onchange_dates(self):
        if not self.id and self.date_from and \
           self.date_to is False or self.date_from > self.date_to:
            date_to_with_delta = datetime.datetime.strptime(
                self.date_from,
                tools.DEFAULT_SERVER_DATETIME_FORMAT) + datetime.timedelta(
                hours=HORAS_POR_DIA)
            self.date_to = str(date_to_with_delta)

        # A date De é maior que a date Para?
        self._check_dates()

        # Nenhuma data para definir até agora: Calcule automáticamente com a HOURS_PER_DAY
        if self.date_from and not self.date_to:
            date_to_with_delta = datetime.datetime.strptime(
                self.date_from,
                tools.DEFAULT_SERVER_DATETIME_FORMAT) + datetime.timedelta(hours=HORAS_POR_DIA)
            self.date_to = str(date_to_with_delta)

        # Calcula e ajusta o número de dias
        self._set_duration()

    @classmethod
    def compute_nb_days(self, diff):
        return round(math.floor(diff)) + 1

    @api.multi
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if (record.date_from and record.date_to and
                    record.date_from > record.date_to):
                raise ValidationError('A data de início deve ser anterior à data de término.')

    @api.multi
    def _prepare_leave_from_imposed_day(self):
        self.ensure_one()
        values = {
            'number_of_days_temp': self.number_of_days,
            'name': self.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'type': 'remove',
            'holiday_status_id': self.status_id.id,
        }
        return values
