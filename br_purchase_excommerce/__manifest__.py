# © 2020 By Alexandre Defendi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{  # pylint: disable=C8101,C8103
    'name': 'Compras Importação/Exportação',
    'description': 'Brazilian Import Declaration',
    'version': '0.0.1',
    'category': 'Localisation',
    'license': 'AGPL-3',
    'author': 'Alexandre Defendi',
    'website': 'http://www.xtiger.com,br',
    'contributors': [
    ],
    'depends': [
        'br_purchase_stock',
        'br_foreign_commerce',
    ],
    'data': [
        'views/purchase_stock_view.xml',
    ],
    'qweb': [],
    'installable': True,
    'auto_install': False,
}
