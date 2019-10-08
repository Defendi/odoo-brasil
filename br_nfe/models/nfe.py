from odoo import api, fields, models

class ImportDeclaration(models.Model):
    _inherit = 'br_account.import.declaration'

    invoice_eletronic_line_id = fields.Many2one(
        'invoice.eletronic.item', 'Linha de Documento Eletrônico',
        ondelete='cascade', index=True)

class ImportDeclarationLine(models.Model):
    _inherit = 'br_account.import.declaration.line'

    invoice_line_id = fields.Many2one(
        'account.invoice.line',
        string="Linhas da fatura")

class AccountDocumentRelated(models.Model):
    _inherit = 'br_account.document.related'

    invoice_eletronic_id = fields.Many2one(
        'invoice.eletronic', 'Documento Eletrônico', ondelete='cascade')

    @api.onchange('invoice_related_id')
    def onchange_br_nfe_invoice_related_id(self):
        if len(self.invoice_related_id.invoice_eletronic_ids) > 0:
            self.access_key = \
                self.invoice_related_id.invoice_eletronic_ids[0].chave_nfe


class NfeReboque(models.Model):
    _name = 'nfe.reboque'
    _description = """Reboque"""

    invoice_eletronic_id = fields.Many2one('invoice.eletronic', string="NFe")
    placa_veiculo = fields.Char(string="Placa", size=7)
    uf_veiculo = fields.Char(string="UF Veículo", size=2)
    rntc = fields.Char(string="RNTC", size=20,
                       help="Registro Nacional de Transportador de Carga")
    vagao = fields.Char(string="Vagão", size=20)
    balsa = fields.Char(string="Balsa", size=20)


class NfeVolume(models.Model):
    _name = 'nfe.volume'
    _description = """Volume"""

    invoice_eletronic_id = fields.Many2one('invoice.eletronic', string="NFe")
    quantidade_volumes = fields.Integer(string="Qtde. Volumes")
    especie = fields.Char(string="Espécie", size=60)
    marca = fields.Char(string="Marca", size=60)
    numeracao = fields.Char(string="Numeração", size=60)
    peso_liquido = fields.Float(string="Peso Líquido")
    peso_bruto = fields.Float(string="Peso Bruto")


class NFeCobrancaDuplicata(models.Model):
    _name = 'nfe.duplicata'
    _order = 'data_vencimento'
    _description = """Duplicata"""

    invoice_eletronic_id = fields.Many2one('invoice.eletronic', string="NFe")
    currency_id = fields.Many2one(
        'res.currency', related='invoice_eletronic_id.currency_id',
        string="EDoc Currency", readonly=True)
    numero_duplicata = fields.Char(string="Número Duplicata", size=60)
    data_vencimento = fields.Date(string="Data Vencimento")
    valor = fields.Monetary(string="Valor Duplicata")

class NFePagamentos(models.Model):
    _name = 'nfe.pagamento'
    _description = """Pagamento"""

    invoice_eletronic_id = fields.Many2one('invoice.eletronic', string="NFe")
    forma_pagamento = fields.Selection([('0','Pagamento à vista'),
                                        ('1','Pagamento a prazo'),
                                        ('2','Outros')],string='Ind.Forma Pgto.')
    metodo_pagamento = fields.Selection(
        [('01', 'Dinheiro'),
         ('02', 'Cheque'),
         ('03', 'Cartão de Crédito'),
         ('04', 'Cartão de Débito'),
         ('05', 'Crédito Loja'),
         ('10', 'Vale Alimentação'),
         ('11', 'Vale Refeição'),
         ('12', 'Vale Presente'),
         ('13', 'Vale Combustível'),
         ('14', 'Duplicata Mercantil'),
         ('15', 'Boleto Bancário'),
         ('90', 'Sem pagamento'),
         ('99', 'Outros')],
        string="Forma de Pagamento", default="01")
    
    valor = fields.Float(string="Valor Pagamento",default=0.0)
