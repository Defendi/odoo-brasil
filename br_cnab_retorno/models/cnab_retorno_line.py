# 11.0.0.1 - 06/2019 - Versão Inicial Alexandre Defendi

import base64
from datetime import datetime

from odoo import models, fields, api
from odoo.exceptions import UserError

# TODO: Inserir toda a tabela
MSG_MOTIVO = {
    '02': 'Entrada Confirmada',
    '03': 'Entrada Rejeitada',
    '04': 'Alteração de Dados Acatado',
    '05': 'Alteração de Dados Baixa',
    '06': 'Liquidação Normal',
    '08': 'Liquidação Cartório',
    '09': 'Baixa Simples',
    '10': 'Baixa por Liquidação',
    '11': 'Em Ser',
    '12': 'Abatimento Concedido',
    '13': 'Abatimento Cancelado',
    '14': 'Confirmação Recebimento Instrução Alteração de Vencimento',
    '15': 'Vencimento Alterado',
    '16': 'Vencimento Alterado',
    '17': 'Alteração/Exclusão de dados rejeitada',
    '27': 'Confirmação do Pedido de Alteração de Outros Dados',
    '28': 'Débito de Tarifas/Custas',
    '29': 'Tarifa de Manutenção de Títulos Vencídos',
}

_STATUS = [
    ('draft', 'Aberto'),
    ('done', 'Processado'),
    ('none', 'Não Tratado'),
    ('fail', 'Falho'),
    ('cancel', 'Cancelado'),
]

class CnabRetornoLine(models.Model):
    _name = "cnab.retorno.line"

    partner_name = fields.Char(string='Parceiro')
    numero_documento = fields.Char(string='Número Documento')
    nosso_numero = fields.Char(string='Nosso Número')
    cod_motivo = fields.Char(string='Código')
    msg_motivo = fields.Char(string='Motivo', compute="_set_motivo", store=True)
    data_vencimento = fields.Date(string='Data Vencimento',default=datetime.now())
    valor = fields.Float(string='Valor Processado')
    cnab_retorno_id = fields.Many2one(string='Cnab Retorno',comodel_name='cnab.retorno',index=True, required=True, ondelete='cascade')
    cnab_retorno_state = fields.Selection(string='Estado Cnab Retorno',related='cnab_retorno_id.state', readonly=True)
    note = fields.Text('Notas')
    state = fields.Selection(_STATUS, string='Estatus',default='draft')
    moveline_id = fields.Many2one(string='Título',comodel_name='account.move.line')
    move_id = fields.Many2one(string='Lançamento Diário',comodel_name='account.move')
    statementline_id = fields.Many2one("account.bank.statement.line", string="Linha Extrato", readonly=True)

    @api.depends('cod_motivo')
    def _set_motivo(self):
        for line in self:
            if MSG_MOTIVO.get(line.cod_motivo.zfill(2)):
                line.msg_motivo = MSG_MOTIVO[line.cod_motivo.zfill(2)]
            else:
                line.msg_motivo = "Motivo não implementado, consulte o manual cnab do banco."
                 
    def cancel_cnab(self):
        for line in self:
            if line.cnab_retorno_id.statement_id.state != 'open':
                line.cnab_retorno_id.statement_id.state = 'open'
            if line.statementline_id:
                line.statementline_id.button_cancel_reconciliation()    
                line.statementline_id.unlink()
    
    def none_cnab(self):
        for line in self:
            line.valor = 0
            line.state = 'none'
