from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    tipo_ambiente = fields.Selection(
        [("1", "Produção"), ("2", "Homologação")],
        string="Ambiente NFe",
        default="2",
    )

    cabecalho_danfe = fields.Selection([('vertical', 'Modelo Vertical'),
                                        ('horizontal', 'Modelo Horizontal')],
                                       string="Cabeçalho Danfe",
                                       default='vertical')

    nfe_sinc = fields.Boolean(string="Aceita envio síncrono")

    iest_ids = fields.One2many(
        'res.company.iest', 'company_id', string="Inscrições Estaduais ST")


class ResCompanyIest(models.Model):
    _name = 'res.company.iest'
    _description = """Inscrição Estadual"""

    name = fields.Char(string="Inscrição Estadual", required=True)
    state_id = fields.Many2one('res.country.state', string="Estado", required=True)
    company_id = fields.Many2one('res.company', string="Empresa", required=True)
