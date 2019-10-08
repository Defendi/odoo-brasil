# 11.0.0.1 - 06/2019 - Versão Inicial Alexandre Defendi

import logging
import base64

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.addons.br_cnab_retorno.models.account_bank_statement_import import SUCCESS_CNAB_RETURN

_logger = logging.getLogger(__name__)

class CnabRetorno(models.Model):
    _name = "cnab.retorno"
    _order = 'data_geracao desc'
    _description = """CNAB Retorno"""
    
    @api.depends('eventos_id.valor')
    def tot_credit(self):
        for cnab in self:
            cnab.total_creditado = 0.0
            for line in cnab.eventos_id:
                cnab.total_creditado += line.valor

    name = fields.Char(string='Nome', compute='_get_name')
    company_id = fields.Many2one('res.company', 'Empresa', readonly=True, default=lambda self: self.env.user.company_id.id)
    journal_id = fields.Many2one(string="Diário", comodel_name="account.journal", required=True)
    cnab_file = fields.Binary(string="Arquivo Cnab", required=True)
    cnab_name = fields.Char(string='CNAB name')
    error_message = fields.Char(string="Mensagem Erro", readonly=True)
    state = fields.Selection(string="Situação",selection=[("open", "Aberto"),("erro", "Erro"),("processado", "Processado"),("close","Fechado"),('cancel','Cancelado')],default="open")
    data_geracao = fields.Date(string="Data Geração do Arquivo", readonly=True)
    data_credito = fields.Date(string="Data Crédito do Arquivo", readonly=True)
    currency_id = fields.Many2one(comodel_name='res.currency', related='company_id.currency_id', string="Company Currency")
    total_creditado = fields.Monetary(compute='tot_credit', string="Total Creditado", readonly=True, store=True)
    eventos_id = fields.One2many(string='Eventos', comodel_name='cnab.retorno.line', inverse_name='cnab_retorno_id')
    statement_id = fields.Many2one("account.bank.statement", string="Extrato", readonly=True)

    def unlink(self):
        for cnab in self:
            if cnab.state == "processado":
                raise UserError(
                    "Não é permitido excluir um retorno que já foi processado!\nCancele primeiro."
                )
        super(CnabRetorno, self).unlink()

    def _save_error_state(self, error_message):
        self.error_message = error_message
        self.state = "erro"

    def _get_name(self):
        for record in self:
            if record.journal_id.bank_id.name and record.journal_id.bank_id.bic:
                record.name = "CNAB Retorno {bnk} {bic} {file}".format(
                    bnk=record.journal_id.bank_id.name, 
                    bic=record.journal_id.bank_id.bic, 
                    file=record.cnab_name if record.cnab_name else ''
                )

    def _validar_banco_retorno(self):
        if int(base64.b64decode(self.cnab_file)[0:3]) != int(self.journal_id.bank_id.bic):
            self.write({
                'error_message': "Banco diferente do Selecionado!",
                'state': "erro"
            })

    def _valor_total_creditado(self, move_lines_data):
        total = 0
        for line in move_lines_data:
            total += line['counterpart_aml_dicts'][0]['credit']
        return total

    def set_close(self):
        for cnab in self:
            for line in cnab.eventos_id:
                if line.state == 'fail':
                    raise UserError("Corrija as falhas para poder fechar") 
            if float_compare(cnab.statement_id.total_entry_encoding, cnab.total_creditado,2) == 0: 
                cnab.state = 'close'
            else:
                raise UserError("O total do extrato está diferente do total do CNAB.")
            
    def cancelar_arquivo_cnab(self):
        for cnab_ret in self:
            if cnab_ret.statement_id:
                cnab_ret.statement_id.state = 'open'
                for st_line in cnab_ret.statement_id.line_ids:
                    st_line.button_cancel_reconciliation()
                cnab_ret.statement_id.unlink()
            for evento in cnab_ret.eventos_id:
                if evento.state != 'none':
                    evento.state = 'draft'
        self.eventos_id.unlink()
        self.write({'state': "open"})

    def reprocessar_arquivo_cnab(self):
        self.importar_arquivo_cnab()

    def importar_arquivo_cnab(self):
        self._validar_banco_retorno()
        processador_cnab = self.env['account.bank.statement.import']
        move_line = self.env['account.move.line']

        self.state = "erro"
        cnabs = self.search([('cnab_name','=',self.cnab_name),('id','!=',self.id)])
        for cnab in cnabs:
            if self.state == 'processado':
                if cnab.state == 'processado':
                    cnab.cancelar_arquivo_cnab()
                cnab.unlink()
            else:
                if cnab.state == 'processado':
                    self.env.cr.commit()
                    raise UserError("Já existe um aruivo com o mesmo nome processado.")

        for evento in self.eventos_id:
            if evento.move_id: 
                evento.state = 'done'
                 
        arquivo = processador_cnab.with_context(journal_id = self.journal_id)._parse_cnab(base64.b64decode(self.cnab_file))
        
        moeda, account_number, vals_bank_statement, move_lines_data, cnab_lines = \
            processador_cnab.with_context(journal_id=self.journal_id)._get_bankstatment(arquivo, self.journal_id, self)

        if len(vals_bank_statement) > 0:
            try:
                if not self.statement_id:
                    self.statement_id = processador_cnab.with_context(journal_id=self.journal_id)._create_statement(vals_bank_statement[0], account_number)
                else:
                    vals_bank_statement[0]['statement_id'] = self.statement_id
                    processador_cnab.with_context(journal_id=self.journal_id)._create_statement(vals_bank_statement[0], account_number)
            except Exception as e:
                if not hasattr(e, 'message'):
                    self.write({'error_message': e.message, 'state': 'erro'})
                else:
                    self.write({'error_message': e, 'state': 'erro'})
                return False
            if self.statement_id:
                statement_lines = self.env['account.bank.statement.line'].search([('statement_id','=',self.statement_id.id),('journal_entry_ids', '=', False)],order="id")
                #self.statement_id.order_id.line_ids
                for statement_line, account_move_data in zip(statement_lines, move_lines_data):
                    move_back_id = account_move_data['counterpart_aml_dicts'][0].get('counterpart_aml_id',False)
                    erro = False
                    if any(line.journal_entry_ids for line in statement_line):
                        for line in statement_line: 
                            account_move_data['counterpart_aml_dicts'][0]['move_id'] = line.journal_entry_ids
                            break
                    else:
                        for move_line_id in account_move_data['counterpart_aml_dicts']:
                            move = move_line.browse(move_line_id['counterpart_aml_id'])
                            if move.full_reconcile_id:
                                erro = move.id
                                break

                        if not erro:                                
                            try:
                                statement_line.process_reconciliations([account_move_data])
                            except Exception as e:
                                if not hasattr(e, 'message'):
                                    erro = e.message
                                else:
                                    erro = e
                    move_find = False
                    for evento in self.eventos_id:
                        if evento.moveline_id.id == move_back_id:
                            move_find = True
                            evento.statementline_id = statement_line
                            if not erro: 
                                evento.state = 'done'
                                evento.move_id = account_move_data['counterpart_aml_dicts'][0]['move_id']
                                evento.note = 'Processado com Sucesso'
                            else:
                                evento.state = 'fail'
                                evento.move_id = False
                                evento.note = erro
                            break
                        
                    if not move_find:
                        for i in range(len(cnab_lines)):
                            if cnab_lines[i].get('moveline_id',False) and cnab_lines[i]['moveline_id'] == move_back_id:
                                cnab_lines[i]['statementline_id'] = statement_line.id
                                if not erro:
                                    cnab_lines[i]['state'] = 'done'
                                    cnab_lines[i]['moveline_id'] = move_back_id
                                    cnab_lines[i]['move_id'] = account_move_data['counterpart_aml_dicts'][0]['move_id']
                                    cnab_lines[i]['note'] = 'Processado com Sucesso'
                                elif isinstance(erro,int):
                                    ml = move_line.browse(erro)
                                    statement_line.unlink()
                                    statement_line = ml.statement_id.id
                                    cnab_lines[i]['state'] = 'done'
                                    cnab_lines[i]['moveline_id'] = erro
                                    cnab_lines[i]['move_id'] = ml.move_id.id
                                    cnab_lines[i]['statementline_id'] = ml.statement_id.id
                                    cnab_lines[i]['note'] = 'Reconciliado Anteriormente'
                                break
        data_geracao_inteira = str(arquivo.header.arquivo_data_de_geracao).zfill(8)
        data_geracao = "{0}-{1}-{2}".format(
            data_geracao_inteira[4:],
            data_geracao_inteira[2:4],
            data_geracao_inteira[:2]
        )

        if arquivo.lotes[0].header._campos.get('data_credito',False):
            data_credito_inteira = str(arquivo.lotes[0].header.data_credito).zfill(8)
            data_credito = "{0}-{1}-{2}".format(
                data_credito_inteira[4:],
                data_credito_inteira[2:4],
                data_credito_inteira[:2],
            )
        else:
            data_credito = False

        lines = []
        total = 0.0
        for line in cnab_lines:
            total += line['valor']
            lines.append((0,0,line))
        exist_fail = False
        for evento in self.eventos_id:
            if evento.state == 'fail':
                exist_fail = True
            if evento.state == 'done':
                total += evento.valor
                
        self.write(
            {
                'state': 'close' if exist_fail else  'processado',
                'data_geracao': data_geracao if data_geracao != '0000-00-00' else False,
                'data_credito': data_credito if data_credito != '0000-00-00' else False,
                'total_creditado': total,
                'error_message': '',
                'eventos_id': lines if lines else False,
            }
        )
