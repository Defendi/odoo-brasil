# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{  # pylint: disable=C8101,C8103
    'name': 'Envio de NFC-e',
    'summary': """Permite o envio de NFC-e através das faturas do Odoo
    Mantido por Trustcode""",
    'description': 'Envio de NFC-e',
    'version': '11.0.1.0.0',
    'category': 'account',
    'author': 'Trustcode',
    'license': 'AGPL-3',
    'website': 'http://www.trustcode.com.br',
    'contributors': [
        'Danimar Ribeiro <danimaribeiro@gmail.com>',
    ],
    'depends': [
        'br_nfe',
    ],
    'external_dependencies': {
        'python': [
            'pytrustnfe', 'pytrustnfe.nfe',
            'pytrustnfe.certificado', 'pytrustnfe.utils'
        ],
    },
    'data': [
        'views/account_invoice.xml',
        'views/invoice_eletronic.xml',
        'views/res_company.xml',
    ],
    'installable': True,
    'application': True,
}
