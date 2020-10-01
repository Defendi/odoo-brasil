# © 2020 By Alexandre Defendi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{  # pylint: disable=C8101,C8103
    'name': 'Odoo Brasil - Módulo Declaração de Importação',
    'description': 'Brazilian Import Declaration',
    'version': '0.0.1',
    'category': 'Localisation',
    'license': 'AGPL-3',
    'author': 'Alexandre Defendi',
    'website': 'http://www.xtiger.com,br',
    'contributors': [
    ],
    'depends': [
        'account',
        'br_account_einvoice',
    ],
    'external_dependencies': {
    },
    'data': [
        'views/import_declaration_view.xml',
        'views/account_fiscal_position_view.xml',
        'views/account_invoice_view.xml',
    ],
    'qweb': [],
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init',
}
