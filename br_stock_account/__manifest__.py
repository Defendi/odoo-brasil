{
    'name': 'Odoo Brasil - WMS Accounting',
    'summary': """Realiza o link entre faturas e o estoque e logistica""",
    'description': 'Odoo Brasil - WMS Accounting',
    'version': '11.0.1.0.0',
    'category': 'account',
    'author': 'Trustcode',
    'license': 'AGPL-3',
    'website': 'http://www.trustcode.com.br',
    'contributors': [
        'Danimar Ribeiro <danimaribeiro@gmail.com>',
    ],
    'depends': [
        'stock_account', 'br_account', 'br_account_einvoice'
    ],
    'data': [
        'views/account_invoice.xml',
        'views/stock_picking.xml',
        'views/product_package_view.xml',
        'reports/account_invoice.xml',
    ],
    'auto_install': True,
}
