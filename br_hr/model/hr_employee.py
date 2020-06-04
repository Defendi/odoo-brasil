# © 2014 KMEE (http://www.kmee.com.br)
# @author Rafael da Silva Lima <rafael.lima@kmee.com.br>
# @author Matheus Felix <matheus.felix@kmee.com.br>
# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError
from odoo.addons.br_base.tools import fiscal

class HrDependentType(models.Model):
    _name = "hr.employee.dependent.type"
    _description = 'Employee\'s Dependents Type'
    
    code            = fields.Char('Código', size=5, required=True)
    name            = fields.Char('Nome', required=True, index=True)
    is_dependent    = fields.Boolean('É dependente', required=False, default=True)

class HrEmployeeDependent(models.Model):
    _name = 'hr.employee.dependent'
    _description = 'Employee\'s Dependents'

    @api.one
    @api.constrains('dependent_cpf')
    def _check_dependent_cpf(self):
        if self.dependent_cpf and not fiscal.validate_cpf(self.dependent_cpf):
            raise ValidationError('CPF do dependente %s inválido!' % self.dependent_name)
        return True

    @api.one
    @api.constrains('dependent_birthday')
    def _check_birth(self):
        dep_age = datetime.strptime(self.dependent_birthday, DEFAULT_SERVER_DATE_FORMAT)
        if dep_age.date() > datetime.now().date():
            raise ValidationError(_('Data de aniversário inválida'))
        return True

    @api.one
    @api.depends('dependent_birthday')
    def _compute_dependent_age(self):
        self.dependent_age_vl = 0
        if self.dependent_birthday:
            dt_today = date.today()
            dt_age = datetime.strptime(self.dependent_birthday, DEFAULT_SERVER_DATE_FORMAT)
            self.dependent_age_vl = relativedelta(dt_today, dt_age).years

    employee_id = fields.Many2one('hr.employee', 'Funcionário')
    dependent_name = fields.Char('Nome', size=64, required=True, translate=True)
    dependent_cpf = fields.Char('CPF', size=14, copy=False)
    dependent_birthday = fields.Date('Data Nascimento', required=True, oldname='dependent_age')
    dependent_age_vl = fields.Integer('Idade', compute='_compute_dependent_age', store=False, readonly=True)
    dependent_type_id = fields.Many2one('hr.employee.dependent.type', u'Tipo', required=True)
    is_dependent = fields.Boolean(related='dependent_type_id.is_dependent')
    pension_benefits = fields.Float('% Pensão', help="Percentual a descontar de pensão alimenticia")
    use_health_plan = fields.Boolean(u'Plano de saúde?', required=False)
    irrf_is = fields.Boolean("IRRF")

    @api.onchange('dependent_cpf')
    def _onchange_cpf(self):
        if bool(self.dependent_cpf):
            val = re.sub('[^0-9]', '', self.dependent_cpf)
            x = len(val)
            if x == 11:
                vlcpf = "%s.%s.%s-%s" % (val[0:3], val[3:6], val[6:9], val[9:11])
                self.dependent_cpf = vlcpf
            elif x > 0:
                raise ValidationError('Verifique o CPF!')

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.multi
    def zip_search(self, cep):
        self.zip = "%s-%s" % (cep[0:5], cep[5:8])
        res = self.env['br.zip'].search_by_zip(zip_code=self.zip)
        if res:
            self.update(res)
        else:
            return {
                'warning': {
                    'title': 'Pesquisa de CEP',
                    'message': 'Nenhum CEP encontrado!',
                }
            }

    def _get_country(self):
        res = self.env['res.country'].search([('name','ilike','Brasil')])
        if res:
            return res
        else:
            return False

    @api.multi
    @api.depends('dependent_ids','have_dependent')
    def _number_dependents(self):
        for item in self:
            if item.have_dependent: 
                item.no_of_dependent = sum(1 if x.is_dependent else 0 for x in item.dependent_ids)
                item.no_of_dependent_health_plan = sum(1 if x.use_health_plan else 0 for x in item.dependent_ids)
                item.no_of_dependent_children = sum(1 if x.dependent_type_id.code in ('03','04','10') else 0 for x in item.dependent_ids)
            else:
                item.no_of_dependent = 0
                item.no_of_dependent_health_plan = 0
                item.no_of_dependent_children = 0

    @api.one
    @api.constrains('pis_pasep')
    def _validate_pis_pasep(self):
        if not self.pis_pasep:
            return True

        digits = []
        for c in self.pis_pasep:
            if c == '.' or c == ' ' or c == '\t':
                continue

            if c == '-':
                if len(digits) != 10:
                    raise ValidationError(_("PIS/PASEP Inválido"))
                continue

            if c.isdigit():
                digits.append(int(c))
                continue

            raise ValidationError(_("PIS/PASEP Inválido"))
        if len(digits) != 11:
            raise ValidationError(_("PIS/PASEP Inválido"))

        height = [int(x) for x in "3298765432"]

        total = 0

        for i in range(10):
            total += digits[i] * height[i]

        rest = total % 11
        if rest != 0:
            rest = 11 - rest
        if rest != digits[10]:
            raise ValidationError(_("PIS/PASEP Inválido"))

    @api.one
    @api.depends('birthday')
    def _compute_employee_age(self):
        self.employee_age = 0
        if self.birthday:
            dt_today = date.today()
            dt_age = datetime.strptime(self.birthday, DEFAULT_SERVER_DATE_FORMAT)
            self.employee_age = relativedelta(dt_today, dt_age).years

    @api.one
    @api.constrains('cpf')
    def _check_cpf(self):
        if self.cpf and not fiscal.validate_cpf(self.cpf):
            raise ValidationError('CPF do funcionário %s inválido.' % self.name)
        return True

    rg = fields.Char('RG', help='Número do RG')
    rg_organ_exp = fields.Char('Orgão de expedição', oldname='organ_exp')
    rg_emission = fields.Date('Data de emissão')

    cpf = fields.Char("CPF", size=14)

    title_voter = fields.Char('Title', help=u'Número título')
    zone_voter = fields.Char('Zona')
    session_voter = fields.Char(u'Secção')
    
    pis_pasep = fields.Char(u'PIS/PASEP', size=15)

    ctps = fields.Char('CTPS', help='Número da CTPS')
    ctps_series = fields.Char('Série')
    ctps_date = fields.Date('Data de emissão')
    
    cert_res_nr = fields.Char('Cert.Reservista', size=25, oldname="creservist")
    cert_res_categ = fields.Char('Categ.C.Reser.', size=10, oldname="crresv_categ")

    driver_license = fields.Char('Carteira de motorista', help=u'Número da carteira de motorista')
    driver_categ = fields.Char('Categoria')
    driver_validate   = fields.Date('Data Validade', oldname="validade")

    father_name = fields.Char('Nome do Pai')
    mother_name = fields.Char('Nome da Mãe')

    sindicate_id = fields.Many2one('res.partner', 'Sindicato')  

    employee_age = fields.Integer('Idade', compute='_compute_employee_age', store=False, readonly=True)

    cr_categ = fields.Selection([('estagiario', u'Estagiário'),('junior', u'Júnior'),('pleno', 'Pleno'),('senior', u'Sênior')],string='Categoria')
    ginstru = fields.Selection(
        [('fundamental_incompleto', 'Basic Education incomplete'),
         ('fundamental', 'Basic Education complete'),
         ('medio_incompleto', 'High School incomplete'),
         ('medio', 'High School complete'),
         ('superior_incompleto', 'College Degree incomplete'),
         ('superior', 'College Degree complete'),
         ('mestrado', 'Master'),
         ('doutorado', 'PhD')],
        string='Schooling', help="Select Education")
    cor  = fields.Selection(
        [('branco', 'Branca'),
         ('negro', 'Negra'),
         ('pardo', 'Parda'),
         ('amarelo', 'Amarela')], string='Cor')

    have_dependent = fields.Boolean("Possui dependentes")
    dependent_ids = fields.One2many('hr.employee.dependent', 'employee_id', 'Dependentes')
    no_of_dependent = fields.Integer('Total',compute=_number_dependents,readonly=True)
    no_of_dependent_health_plan = fields.Integer('Plano Saúde',compute=_number_dependents,readonly=True)
    no_of_dependent_children = fields.Integer('Menores',compute=_number_dependents,readonly=True)

    # Nacionalidade
    nationality_id = fields.Many2one('res.country', 'Nacionalidade (País)',default=_get_country)

    # Endereço
    street = fields.Char('Logradouro')
    number = fields.Char('Número', size=10)
    complement = fields.Char('Complemento')
    district = fields.Char('Bairro', size=32)
    zip = fields.Char(change_default=True)
    country_id = fields.Many2one(comodel_name='res.country', string='País',default=_get_country)
    state_id = fields.Many2one(comodel_name='res.country.state', string='Estado', domain="[('country_id','=',country_id)]")
    city_id = fields.Many2one('res.state.city', 'Município', domain="[('state_id','=',state_id)]")
    # Contact
    personal_phone = fields.Char('Telefone Pessoal')
    personal_mobile = fields.Char('Celular Pessoal')
    personal_email = fields.Char('E-mail Pessoal')

    # Bank Data
    bank_id = fields.Many2one('res.bank', string='Banco')
    acc_number = fields.Char('Account Number', size=64, required=False)
    acc_number_dig = fields.Char('Account Number Digit', size=8)
    bra_number = fields.Char('Agency', size=10)
    bra_number_dig = fields.Char('Account Agency Digit', size=8)

    @api.onchange('cpf')
    def _onchange_cpf(self):
        if bool(self.cpf):
            val = re.sub('[^0-9]', '', self.cpf)
            x = len(val)
            if x == 11:
                vlcpf = "%s.%s.%s-%s" % (val[0:3], val[3:6], val[6:9], val[9:11])
                self.cpf = vlcpf
            elif x > 0:
                raise ValidationError('Verifique o CPF!')

    @api.onchange('zip')
    def _onchange_zip(self):
        if bool(self.zip):
            cep = re.sub('[^0-9]', '', self.zip)
            x = len(cep)
            if x == 8:
                vlzip = "%s-%s" % (cep[0:5], cep[5:8])
                self.zip = vlzip
                self.zip_search(cep)
            elif x > 0:
                raise ValidationError('Verifique o CEP!')

    @api.onchange('name')
    def _onchange_name(self):
        if bool(self.name):
            res_partner = self.env['res.partner'].search([('name','ilike',self.name)],limit=1)
            if bool(res_partner) and not bool(self.address_home_id):
                self.address_home_id = res_partner
                
    @api.onchange('address_home_id')
    def _onchange_address_home_id(self):
        if bool(self.address_home_id):
            self.street = self.address_home_id.street
            self.number = self.address_home_id.number
            self.complement = self.address_home_id.street2
            self.district = self.address_home_id.district
            self.zip = self.address_home_id.zip
            self.country_id = self.address_home_id.country_id
            self.state_id = self.address_home_id.state_id
            self.city_id = self.address_home_id.city_id
            

