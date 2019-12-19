from odoo import models, fields, api

NFSE_NAT_OPER = [
    ("101","ISS devido para Itajaí"),
    ("111","ISS devido para outro município"),
    ("121","ISS Fixo (Soc. Profissionais)"),
    ("201","ISS retido pelo tomador/intermediário"),    
    ("301","Operação imune, isenta ou não tributada"),
    ("501","ISS devido para Itajaí (Simples Nacional)"),
    ("511","ISS devido para outro município (Simples Nacional)"),
    ("541","MEI (Simples Nacional)"),
    ("551","Escritório Contábil (Simples Nacional)"),
    ("601","ISS retido pelo tomador/intermediário (Simples Nacional)"),
    ("701","Operação imune, isenta ou não tributada (Simples Nacional)"),
]

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    nfse_itajai_nat_oper = fields.Selection(NFSE_NAT_OPER, string="Natureza Opera",default="101")

    def _return_pdf_invoice(self, doc):
        if doc.model == '203':
            return {'warning': {'title': _("Ops!"), 'message': 'Não implementado'}} 
        return super(AccountInvoice, self)._return_pdf_invoice(doc)

    def _prepare_edoc_item_vals(self, line):
        res = super(AccountInvoice, self)._prepare_edoc_item_vals(line)
        return res
