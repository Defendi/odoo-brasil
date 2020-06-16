from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

from odoo.addons.br_base.tools import fiscal
from .cst import CST_ICMS

class BrAccountCFOP(models.Model):
    """CFOP - Código Fiscal de Operações e Prestações"""
    _name = 'br_account.cfop'
    _description = 'CFOP'

    code = fields.Char('Código', size=4, required=True)
    name = fields.Char('Nome', size=256, required=True)
    small_name = fields.Char('Nome Reduzido', size=32, required=True)
    description = fields.Text('Descrição')
    type = fields.Selection([('input', 'Entrada'),
                             ('output', 'Saída')],
                            'Tipo', required=True)
    parent_id = fields.Many2one(
        'br_account.cfop', 'CFOP Pai')
    child_ids = fields.One2many(
        'br_account.cfop', 'parent_id', 'CFOP Filhos')
    internal_type = fields.Selection(
        [('view', 'Visualização'), ('normal', 'Normal')],
        'Tipo Interno', required=True, default='normal')

    _sql_constraints = [
        ('br_account_cfop_code_uniq', 'unique (code)',
            'Já existe um CFOP com esse código !')
    ]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "%s - %s" % (rec.code, rec.name or '')))
        return result


class BrAccountServiceType(models.Model):
    _name = 'br_account.service.type'
    _description = 'Cadastro de Operações Fiscais de Serviço'

    code = fields.Char('Código', size=16, required=True)
    name = fields.Char('Descrição', size=256, required=True)
    parent_id = fields.Many2one(
        'br_account.service.type', 'Tipo de Serviço Pai')
    child_ids = fields.One2many(
        'br_account.service.type', 'parent_id',
        'Tipo de Serviço Filhos')
    internal_type = fields.Selection(
        [('view', 'Visualização'), ('normal', 'Normal')], 'Tipo Interno',
        required=True, default='normal')
    federal_nacional = fields.Float('Imposto Fed. Sobre Serviço Nacional')
    federal_importado = fields.Float('Imposto Fed. Sobre Serviço Importado')
    estadual_imposto = fields.Float('Imposto Estadual')
    municipal_imposto = fields.Float('Imposto Municipal')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "%s - %s" % (rec.code, rec.name or '')))
        return result


class BrAccountFiscalDocument(models.Model):
    _name = 'br_account.fiscal.document'
    _description = 'Tipo de Documento Fiscal'

    code = fields.Char('Codigo', size=8, required=True)
    name = fields.Char('Descrição', size=64)
    electronic = fields.Boolean('Eletrônico')
    nfse_eletronic = fields.Boolean('Emite NFS-e?')


class BrAccountDocumentSerie(models.Model):
    _name = 'br_account.document.serie'
    _description = 'Série de documentos fiscais'

    code = fields.Char('Código', size=3, required=True)
    name = fields.Char('Descrição', required=True)
    active = fields.Boolean('Ativo')
    fiscal_type = fields.Selection([('service', 'Serviço'),
                                    ('product', 'Produto')], 'Tipo Fiscal',
                                   default='service')
    fiscal_document_id = fields.Many2one('br_account.fiscal.document',
                                         'Documento Fiscal', required=True)
    company_id = fields.Many2one('res.company', 'Empresa',
                                 required=True)
    internal_sequence_id = fields.Many2one('ir.sequence',
                                           'Sequência Interna')

    lot_sequence_id = fields.Many2one('ir.sequence',
                                           'Sequência Lote')

    @api.model
    def _create_sequence(self, vals, lote=False):
        """ Create new no_gap entry sequence for every
         new document serie """
        seq = {
            'name': 'lote_'+vals['name'] if lote else vals['name'],
            'implementation': 'no_gap',
            'padding': 1,
            'number_increment': 1}
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq).id

    @api.model
    def create(self, vals):
        """ Overwrite method to create a new ir.sequence if
         this field is null """
        if not vals.get('internal_sequence_id'):
            vals.update({'internal_sequence_id': self._create_sequence(vals)})
        return super(BrAccountDocumentSerie, self).create(vals)


class BrAccountCNAE(models.Model):
    _name = 'br_account.cnae'
    _description = 'Cadastro de CNAE'

    code = fields.Char('Código', size=16, required=True)
    name = fields.Char('Descrição', size=64, required=True)
    version = fields.Char('Versão', size=16, required=True)
    parent_id = fields.Many2one('br_account.cnae', 'CNAE Pai')
    child_ids = fields.One2many(
        'br_account.cnae', 'parent_id', 'CNAEs Filhos')
    internal_type = fields.Selection(
        [('view', 'Visualização'), ('normal', 'Normal')],
        'Tipo Interno', required=True, default='normal')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "%s - %s" % (rec.code, rec.name or '')))
        return result


class ImportDeclaration(models.Model):
    _name = 'br_account.import.declaration'
    _description = """Declaração de Importação"""

    def _compute_invoice(self):
        for di in self:
            inv_lines = self.env['account.invoice.line'].search([('import_declaration_ids','in',[di.id])])
            inv_ids = []
            for inv_line in inv_lines:
                if inv_line.invoice_id.id not in inv_ids:
                    inv_ids.append(inv_line.invoice_id.id)
            invoices = self.env['account.invoice'].browse(inv_ids)
            di.invoice_ids = invoices
            di.invoice_count = len(invoices)

    invoice_ids = fields.Many2many('account.invoice', compute="_compute_invoice", string='Bills', store=False)
    invoice_count = fields.Integer(compute="_compute_invoice", string='# Faturas', copy=False, default=0, store=False)
    name = fields.Char('Número da DI', size=10, required=True)
    date_registration = fields.Date('Data de Registro', required=True)
    state_id = fields.Many2one('res.country.state', 'Estado',domain="[('country_id.code', '=', 'BR')]", required=True)
    location = fields.Char('Local', required=True, size=60)
    date_release = fields.Date('Data de Liberação', required=True)
    type_transportation = fields.Selection([
        ('1', '1 - Marítima'),
        ('2', '2 - Fluvial'),
        ('3', '3 - Lacustre'),
        ('4', '4 - Aérea'),
        ('5', '5 - Postal'),
        ('6', '6 - Ferroviária'),
        ('7', '7 - Rodoviária'),
        ('8', '8 - Conduto / Rede Transmissão'),
        ('9', '9 - Meios Próprios'),
        ('10', '10 - Entrada / Saída ficta'),
    ], 'Transporte Internacional', required=True, default="1")
    afrmm_value = fields.Float('Valor da AFRMM', digits=dp.get_precision('Account'), default=0.00)
    type_import = fields.Selection([
        ('1', '1 - Importação por conta própria'),
        ('2', '2 - Importação por conta e ordem'),
        ('3', '3 - Importação por encomenda'),
    ], 'Tipo de Importação', default='1', required=True)
    thirdparty_cnpj = fields.Char('CNPJ', size=18)
    thirdparty_state_id = fields.Many2one('res.country.state', 'Estado',domain="[('country_id.code', '=', 'BR')]")
    exporting_code = fields.Char('Código do Exportador', required=True, size=60)
    additional_information = fields.Text('Informações Adicionais')
    line_ids = fields.One2many('br_account.import.declaration.line','import_declaration_id', 'Linhas da DI')

class ImportDeclarationLine(models.Model):
    _name = 'br_account.import.declaration.line'
    _description = """Linha da Declaração de Importação"""

    import_declaration_id = fields.Many2one('br_account.import.declaration', 'DI', ondelete='cascade')
    sequence = fields.Integer('Sequência', default=1, required=True)
    name = fields.Char('Adição', size=3, required=True)
    manufacturer_code = fields.Char('Código do Fabricante', size=60, required=True)
    amount_discount = fields.Float(string='Desconto', digits=dp.get_precision('Account'), default=0.00)
    drawback_number = fields.Char('Número Drawback', size=11)


class AccountDocumentRelated(models.Model):
    _name = 'br_account.document.related'
    _description = """Documento relacionado"""

    invoice_id = fields.Many2one('account.invoice', 'Documento Fiscal',
                                 ondelete='cascade')
    invoice_related_id = fields.Many2one(
        'account.invoice', 'Documento Fiscal', ondelete='cascade')
    document_type = fields.Selection(
        [('nf', 'NF'), ('nfe', 'NF-e'), ('cte', 'CT-e'),
            ('nfrural', 'NF Produtor'), ('cf', 'Cupom Fiscal')],
        'Tipo Documento', required=True)
    access_key = fields.Char('Chave de Acesso', size=44)
    serie = fields.Char('Série', size=12)
    internal_number = fields.Char('Número', size=32)
    state_id = fields.Many2one('res.country.state', 'Estado',
                               domain="[('country_id.code', '=', 'BR')]")
    cnpj_cpf = fields.Char('CNPJ/CPF', size=18)
    cpfcnpj_type = fields.Selection(
        [('cpf', 'CPF'), ('cnpj', 'CNPJ')], 'Tipo Doc.',
        default='cnpj')
    inscr_est = fields.Char('Inscr. Estadual/RG', size=16)
    date = fields.Date('Data')
    fiscal_document_id = fields.Many2one(
        'br_account.fiscal.document', 'Documento')

    @api.one
    @api.constrains('cnpj_cpf')
    def _check_cnpj_cpf(self):
        check_cnpj_cpf = True
        if self.cnpj_cpf:
            if self.cpfcnpj_type == 'cnpj':
                if not fiscal.validate_cnpj(self.cnpj_cpf):
                    check_cnpj_cpf = False
            elif not fiscal.validate_cpf(self.cnpj_cpf):
                check_cnpj_cpf = False
        if not check_cnpj_cpf:
            raise UserError(_('CNPJ/CPF do documento relacionado é invalido!'))

    @api.one
    @api.constrains('inscr_est')
    def _check_ie(self):
        check_ie = True
        if self.inscr_est:
            uf = self.state_id and self.state_id.code.lower() or ''
            try:
                mod = __import__('odoo.addons.br_base.tools.fiscal',
                                 globals(), locals(), 'fiscal')

                validate = getattr(mod, 'validate_ie_%s' % uf)
                if not validate(self.inscr_est):
                    check_ie = False
            except AttributeError:
                if not fiscal.validate_ie_param(uf, self.inscr_est):
                    check_ie = False
        if not check_ie:
            raise UserError(
                _('Inscrição Estadual do documento fiscal inválida!'))

    @api.onchange('invoice_related_id')
    def onchange_invoice_related_id(self):
        if not self.invoice_related_id:
            return
        inv_id = self.invoice_related_id
        if not inv_id.product_document_id:
            return

        self.document_type = \
            self.translate_document_type(inv_id.product_document_id.code)

        if inv_id.product_document_id.code in ('55', '57'):
            self.serie = False
            self.internal_number = False
            self.state_id = False
            self.cnpj_cpf = False
            self.cpfcnpj_type = False
            self.date = False
            self.fiscal_document_id = False
            self.inscr_est = False

    def translate_document_type(self, code):
        if code == '55':
            return 'nfe'
        elif code == '04':
            return 'nfrural'
        elif code == '57':
            return 'cte'
        elif code in ('2B', '2C', '2D'):
            return 'cf'
        else:
            return 'nf'


class BrAccountFiscalObservation(models.Model):
    _name = 'br_account.fiscal.observation'
    _description = 'Mensagen Documento Eletrônico'
    _order = 'sequence'

    sequence = fields.Integer('Sequência', default=1, required=True)
    name = fields.Char('Descrição', required=True, size=50)
    message = fields.Text('Mensagem', required=True)
    tipo = fields.Selection([('fiscal', 'Observação Fiscal'),
                             ('observacao', 'Observação')], string="Tipo")
    document_id = fields.Many2one(
        'br_account.fiscal.document', string="Documento Fiscal")


class BrAccountCategoriaFiscal(models.Model):
    _name = 'br_account.fiscal.category'
    _description = 'Categoria Fiscal'

    name = fields.Char('Descrição', required=True)

class BrAccountBeneficioFiscal(models.Model):
    _name = 'br_account.beneficio.fiscal'
    _description = 'Código de Benefício Fiscal'

    code = fields.Char('Código',size=10)
    name = fields.Char('Descrição', required=True)
    state_id = fields.Many2one('res.country.state', 'Estado', domain="[('country_id.code', '=', 'BR')]", required=True)
    dt_start = fields.Date('Data Inicial')
    dt_end = fields.Date('Data Final')
    cst_line_ids = fields.One2many('br_account.beneficio.fiscal.cst', 'beneficio_id', string="CSTs", copy=True)
    memo = fields.Text('Observação')

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "[%s] %s" % (rec.code or '', rec.name or '')))
        return result


class BrAccountBeneficioFiscalCST(models.Model):
    _name = 'br_account.beneficio.fiscal.cst'
    _description = 'CST - Código de Benefício Fiscal'
    
    name = fields.Selection(CST_ICMS, string="CST ICMS")
    beneficio_id = fields.Many2one('br_account.beneficio.fiscal',string='CST - Código de Benefício Fiscal')
    code = fields.Char(related='beneficio_id.code',store=True)
    #name = fields.Char(related='beneficio_id.code')
    state_id = fields.Many2one(related='beneficio_id.state_id',store=True)
    dt_start = fields.Date(related='beneficio_id.dt_start',store=True)
    dt_end = fields.Date(related='beneficio_id.dt_end',store=True)
    
