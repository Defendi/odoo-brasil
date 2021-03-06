# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{  # pylint: disable=C8101,C8103
    'name': 'Envio de NFS-e Itajaí',
    'summary': """Permite o envio de NFS-e Itajaí através das faturas do Odoo Mantido por DocSafe""",
    'description': 'Envio de NFS-e - Itajaí',
    'version': '11.0.1.0.0',
    'category': 'account',
    'author': 'DocSafe',
    'license': 'AGPL-3',
    'website': 'http://www.docsafe.com.br',
    'contributors': [
        'Alexandre Defendi',
    ],
    'depends': [
        'br_nfse',
    ],
    'data': [
#         'views/br_account_service.xml',
#         'views/invoice_eletronic.xml',
    ],
    'installable': True,
    'application': True,
}
